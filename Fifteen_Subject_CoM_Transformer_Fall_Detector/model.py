from __future__ import annotations

import torch
from torch import nn


class CoMTemporalTransformer(nn.Module):
    """Compact temporal-attention classifier for theta/x CoM windows."""

    def __init__(
        self,
        window_length: int = 64,
        input_channels: int = 2,
        d_model: int = 32,
        nhead: int = 4,
        num_layers: int = 2,
        dim_feedforward: int = 128,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        if d_model % nhead:
            raise ValueError("d_model must be divisible by nhead")
        self.window_length = int(window_length)
        self.input_projection = nn.Sequential(
            nn.Conv1d(input_channels, d_model, kernel_size=5, padding=2),
            nn.BatchNorm1d(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.position_embedding = nn.Parameter(
            torch.zeros(1, self.window_length, d_model)
        )
        nn.init.trunc_normal_(self.position_embedding, std=0.02)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers,
            norm=nn.LayerNorm(d_model),
            enable_nested_tensor=False,
        )
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Dropout(dropout),
            nn.Linear(d_model, 1),
        )

    def forward(self, x: torch.Tensor, valid_mask: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3 or x.shape[-1] != 2:
            raise ValueError(f"Expected [batch, time, 2], got {tuple(x.shape)}")
        if valid_mask.shape != x.shape[:2]:
            raise ValueError("valid_mask must have shape [batch, time]")
        if x.shape[1] != self.window_length:
            raise ValueError(
                f"Expected {self.window_length} frames, got {x.shape[1]}"
            )
        mask = valid_mask.bool()
        hidden = self.input_projection(x.transpose(1, 2)).transpose(1, 2)
        hidden = hidden + self.position_embedding[:, : hidden.shape[1]]
        hidden = self.encoder(hidden, src_key_padding_mask=~mask)
        weights = mask.unsqueeze(-1).to(hidden.dtype)
        pooled = (hidden * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)
        return self.head(pooled).squeeze(-1)

