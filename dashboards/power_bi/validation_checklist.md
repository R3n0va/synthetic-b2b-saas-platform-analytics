# Power BI validation checklist

1. Closing MRR reconciles to `reports/samples/mrr_snapshot.csv` for the same month.
2. MRR movements reconcile exactly to the bridge identity.
3. ARR equals MRR multiplied by twelve.
4. Invoice totals reconcile to invoice lines and PostgreSQL quality views.
5. NRR and GRR use the opening installed base only.
6. Cross-currency totals use the governed EUR amount, not ad-hoc conversion.
7. Account counts are distinct at the intended grain.
8. Filters do not create many-to-many propagation between invoice and MRR facts.
9. Experiment results match `reports/samples/experiment_decisions.csv`.
10. Executive cards reconcile to `reports/samples/executive_summary.json`.
