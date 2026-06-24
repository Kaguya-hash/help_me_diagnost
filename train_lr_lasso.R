
# Load only the package needed for LASSO logistic regression
library(glmnet)
library(jsonlite)

# Get the data.frame names from command-line arguments
args <- commandArgs(trailingOnly = TRUE)

df_name1 <- args[1]
df_name2 <- args[2]

df_names <- c(df_name1, df_name2)

# Load the data from stdin
load(file("stdin", "rb"))

# Add subtype labels from the data.frame names and combine the cohorts
for (name in df_names) {
  df <- get(name)
  df$subtype <- name
  assign(name, df)
}
combined_df <- do.call(rbind, lapply(df_names, get))

# Keep only numeric gene features and compute variance per gene
numeric_cols <- sapply(combined_df, is.numeric)
variances <- apply(combined_df[, numeric_cols], 2, var, na.rm = TRUE)

# Remove the lowest 10% by variance
threshold <- quantile(variances, probs = 0.10, na.rm = TRUE)
keep_cols <- names(variances[variances > threshold])
filtered_df <- combined_df[, c("subtype", keep_cols)]
filtered_df$subtype <- factor(filtered_df$subtype)

# Prepare the feature matrix and response vector
x <- as.matrix(filtered_df[, keep_cols])
# Map df_name1 to 1 and df_name2 to 0
y <- ifelse(filtered_df$subtype == df_name1, 1, 0)

# Find the LASSO lambda.1se using 5-fold cross-validation with alpha = 1
set.seed(123)
cv_fit <- cv.glmnet(x, y, family = "binomial", alpha = 1, nfolds = 5, standardize = TRUE)
optimal_lambda <- cv_fit$lambda.1se

# Train the final sparse logistic regression model at lambda.1se
final_lasso_model <- glmnet(x, y, family = "binomial", alpha = 1, lambda = optimal_lambda, standardize = TRUE)

# Save the model coefficients and keep only genes with non-zero weights
coef_mat <- coef(final_lasso_model)

# Convert to vector and select non-zero entries before building the data.frame
coef_vec <- as.vector(coef_mat)
nonzero_idx <- which(coef_vec != 0)

# Order by descending absolute weight and build the data.frame directly
ord <- order(abs(coef_vec[nonzero_idx]), decreasing = TRUE)
final_genes_df <- data.frame(
  Gene = rownames(coef_mat)[nonzero_idx][ord],
  Weight = coef_vec[nonzero_idx][ord],
  stringsAsFactors = FALSE
)

# write the file
cat(toJSON(final_genes_df, dataframe = "columns", auto_unbox = TRUE, digits = NA))