# Weight Change Approval Workflow

## When to Review

A weight change requires manual review when any parameter shifts by more
than 25% relative to the previous version. The `WeightStabilityTracker`
automatically flags these changes.

## Review Process

1. **Generate review template**: Run the weight stability check to
   produce a Markdown comparison table.
2. **Domain expert review**: A domain expert reviews the parameter
   changes and their expected impact on ranking quality.
3. **Backtest**: Run the scoring pipeline on a held-out cohort with
   both old and new weights. Compare rank correlation (Kendall tau >= 0.90).
4. **Approval**: At least one domain expert must approve before deployment.

## Auto-deploy Criteria

If all parameter changes are within the 25% threshold, the new weights
may be auto-deployed without manual review. The CI pipeline will still
run regression tests before deployment.

## Rollback

If post-deploy monitoring detects a regression (score distribution KS > 0.1
or apex recall drop > 5%), immediately rollback to the previous weight version
and open a review ticket.
