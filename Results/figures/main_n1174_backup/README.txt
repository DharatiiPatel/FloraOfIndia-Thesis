Backup of ecology figures published under Results/ before switching to
expansion n=1438 as the figure source of truth.

Created: 2026-08-14T15:36:35-04:00
Contents:
  main/           — fig1–fig5 (+ fig2b) as previously published
  elevation/      — fig6_* from step08_outputs_clean
  supplementary/  — figS traces + coefficient_plot_PC1_PC3
  Processed_Data_figures/ — copy of Processed Data/figures/

Revert:
  cp -a /scratch/dp23301/Thesis/Results/figures/main_n1174_backup/main/*.png /scratch/dp23301/Thesis/Results/figures/main/
  # or re-symlink to Processed Data/figures and step08_outputs_clean
  # then: Rscript scripts/07_Generate_Figures.R
