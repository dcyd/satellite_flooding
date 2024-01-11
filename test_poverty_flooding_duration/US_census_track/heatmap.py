# Function to create heatmap with percentage and value range for each category
def create_heatmap_with_percentage_and_range(flood_df, income_df, flood_column, thresholds, title):
    # Filtering and converting to numeric
    if flood_column == 'flooded_population_sum':
        flood_df_temp = flood_df[flood_df[flood_column] > 0]
    else:
        flood_df_temp = flood_df[flood_df[flood_column].notna()]
    flood_df_temp[flood_column] = pd.to_numeric(flood_df_temp[flood_column])

    # Categorizing based on thresholds
    bins = [-np.inf] + thresholds + [np.inf]
    categories = ['Low', 'Medium', 'High']
    flood_df_temp['Flood Category'] = pd.cut(flood_df_temp[flood_column], bins=bins, labels=categories)

    # Merge with income data
    merged_temp_df = pd.merge(flood_df_temp, income_df[['GEOID', 'Income Category']], on='GEOID', how='inner')

    # Calculate counts and percentages
    counts_temp = merged_temp_df.groupby(['Income Category', 'Flood Category']).size().unstack(fill_value=0)
    percentages_temp = counts_temp.div(counts_temp.sum(axis=1), axis=0)

    # Adding percentage and range to labels
    flood_labels = [f"{cat} ({percentages_temp[cat].sum():.2%}, {bins[i]}-{bins[i+1]})" for i, cat in enumerate(categories)]

    # Returning the percentages and labels for the heatmap
    return percentages_temp, flood_labels

# Creating the 2x2 group of heatmaps with custom thresholds and labels
fig, axs = plt.subplots(2, 2, figsize=(20, 20))
plt.subplots_adjust(hspace=0.5, wspace=0.3)

# Flooded Population Sum
percentages, labels = create_heatmap_with_percentage_and_range(flood_df, income_df_common, 'flooded_population_sum', thresholds_flooded_population_sum, 'Flooded Population Sum')
sns.heatmap(percentages, annot=True, cmap='YlGnBu', fmt=".2%", cbar=False, ax=axs[0, 0])
axs[0, 0].set_title('Flooded Population Sum')
axs[0, 0].set_ylabel('Income Category')
axs[0, 0].set_xlabel('Flood Category')
axs[0, 0].set_xticklabels(labels)

# Duration Max
percentages, labels = create_heatmap_with_percentage_and_range(flood_df, income_df_common, 'duration_max', thresholds_duration_max, 'Duration Max')
sns.heatmap(percentages, annot=True, cmap='YlGnBu', fmt=".2%", cbar=False, ax=axs[0, 1])
axs[0, 1].set_title('Duration Max')
axs[0, 1].set_ylabel('Income Category')
axs[0, 1].set_xlabel('Flood Category')
axs[0, 1].set_xticklabels(labels)

# Duration Mean (Cell)
percentages, labels = create_heatmap_with_percentage_and_range(flood_df, income_df_common, 'duration_mean(cell)', thresholds_duration_mean_cell, 'Duration Mean (Cell)')
sns.heatmap(percentages, annot=True, cmap='YlGnBu', fmt=".2%", cbar=False, ax=axs[1, 0])
axs[1, 0].set_title('Duration Mean (Cell)')
axs[1, 0].set_ylabel('Income Category')
axs[1, 0].set_xlabel('Flood Category')
axs[1, 0].set_xticklabels(labels)

# Duration Mean (Flooded Population)
percentages, labels = create_heatmap_with_percentage_and_range(flood_df, income_df_common, 'duration_mean(flooded population)', thresholds_duration_mean_flooded_population, 'Duration Mean (Flooded Population)')
sns.heatmap(percentages, annot=True, cmap='YlGnBu', fmt=".2%", cbar=False, ax=axs[1, 1])
axs[1, 1].set_title('Duration Mean (Flooded Population)')
axs[1, 1].set_ylabel('Income Category')
axs[1, 1].set_xlabel('Flood Category')
axs[1, 1].set_xticklabels(labels)

plt.show()
