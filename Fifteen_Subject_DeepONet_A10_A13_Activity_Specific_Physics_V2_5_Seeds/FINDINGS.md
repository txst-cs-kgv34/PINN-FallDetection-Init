# Findings — pending seed-1 pilot

No results are claimed in this source package. Run `./run_on_mac.sh pilot mps`
and return the generated pilot-results ZIP.

The comparison script will report:

- selected V2 versus matched from-scratch lambda=0 for normalized forecast MSE,
  theta RMSE, and CoM-x RMSE;
- held-out subject boxplots and paired subject wins;
- descriptive A10/A11/A12/A13 results and activity boxplots;
- lambda selections for all five folds;
- angular and horizontal CartPole residual changes;
- initialization hash equality and exact paired-target equality.

Seed 1 will be treated as a screening result. The five-seed result remains the
confirmatory result if the pilot passes the planned review.

