library(glmnet)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)

load(args[3])

n1 <- nrow(get(args[1]))
n2 <- nrow(get(args[2]))

x <- rbind(
  as.matrix(get(args[1])),
  as.matrix(get(args[2]))
)

rm(list = c(args[1], args[2]))

y <- c(rep(1L, n1), rep(0L, n2))
rm(n1, n2)

# Remove the lowest 10% by variance
variances <- apply(x, 2, var, na.rm = TRUE)
threshold <- quantile(variances, probs = 0.10, na.rm = TRUE)

x <- x[, variances > threshold, drop = FALSE]
rm(variances, threshold)

set.seed(123)
cv_fit <- cv.glmnet(x, y, family = "binomial", alpha = 1, nfolds = 5, standardize = TRUE)
optimal_lambda <- cv_fit$lambda.1se
rm(cv_fit)

final_lasso_model <- glmnet(x, y, family = "binomial", alpha = 1, lambda = optimal_lambda, standardize = TRUE)
rm(x, y, optimal_lambda)

coef_vec <- as.vector(coef(final_lasso_model))
gene_names <- rownames(coef(final_lasso_model))
rm(final_lasso_model)

nonzero_idx <- which(coef_vec != 0)
ord <- order(abs(coef_vec[nonzero_idx]), decreasing = TRUE)
final_genes_df <- data.frame(
  Gene = gene_names[nonzero_idx][ord],
  Weight = coef_vec[nonzero_idx][ord],
  stringsAsFactors = FALSE
)
rm(coef_vec, gene_names, nonzero_idx, ord)

# write the file
cat(toJSON(final_genes_df, dataframe = "columns", auto_unbox = TRUE, digits = NA))
rm(final_genes_df)