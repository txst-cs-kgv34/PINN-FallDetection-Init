import unittest

try:
    import torch
    from model import CoMTemporalTransformer
except ModuleNotFoundError:
    torch = None
    CoMTemporalTransformer = None


class ModelTests(unittest.TestCase):
    @unittest.skipIf(torch is None, "PyTorch is not installed in this validation environment")
    def test_forward(self):
        model=CoMTemporalTransformer(window_length=64); values=torch.zeros(3,64,2); mask=torch.ones(3,64,dtype=torch.bool); self.assertEqual(tuple(model(values,mask).shape),(3,))


if __name__=="__main__": unittest.main()
