function pdf_different_come_duration(subTable)

    % Filter the regions into three groups based on incoMean
    highIncomeRegions = subTable.durCelMax(subTable.incoMean > 6.85);
    middleIncomeRegions = subTable.durCelMax(subTable.incoMean > 3.65 & subTable.incoMean <= 6.85);
    lowIncomeRegions = subTable.durCelMax(subTable.incoMean <= 3.65);
    
    % Fit the exponential distribution to each group and calculate the PDF
    lambda_high = 1 / mean(highIncomeRegions);
    lambda_middle = 1 / mean(middleIncomeRegions);
    lambda_low = 1 / mean(lowIncomeRegions);
    
    % Create a range of x values for plotting the PDFs
    x_values = linspace(0, max(subTable.durCelMax), 100);
    
    % Calculate the exponential PDFs for each group
    pdf_high = exppdf(x_values, 1/lambda_high);
    pdf_middle = exppdf(x_values, 1/lambda_middle);
    pdf_low = exppdf(x_values, 1/lambda_low);
    
    % Plot the histograms and PDFs
    hold on;
    
    % Define colors for each group for consistency
    colors = {'r', 'g', 'b'};
    
    % High income group histogram and PDF
    histogram(highIncomeRegions, 'Normalization', 'pdf', 'DisplayStyle', 'stairs', 'EdgeColor', colors{1});
    plot(x_values, pdf_high, colors{1}, 'LineWidth', 2);
    
    % Middle income group histogram and PDF
    histogram(middleIncomeRegions, 'Normalization', 'pdf', 'DisplayStyle', 'stairs', 'EdgeColor', colors{2});
    plot(x_values, pdf_middle, colors{2}, 'LineWidth', 2);
    
    % Low income group histogram and PDF
    histogram(lowIncomeRegions, 'Normalization', 'pdf', 'DisplayStyle', 'stairs', 'EdgeColor', colors{3});
    plot(x_values, pdf_low, colors{3}, 'LineWidth', 2);
    
    % Labels and title
    xlabel('Duration (durCelMax)');
    ylabel('Probability Density');
    legend('High Income Data', 'High Income Fit', 'Middle Income Data', 'Middle Income Fit', 'Low Income Data', 'Low Income Fit');
    
    % Add text annotations for the parameters
    text('Units', 'normalized', 'Position', [0.5 0.6], 'BackgroundColor', 'white', ...
        'String', sprintf('High Income Lambda: %.3f\nMiddle Income Lambda: %.3f\nLow Income Lambda: %.3f', ...
        lambda_high, lambda_middle, lambda_low), 'EdgeColor', 'black');
    
    hold off;

end