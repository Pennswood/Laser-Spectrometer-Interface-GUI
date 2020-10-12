function averagedTable = avg(path, micros)
    tableAggrevate = []
    for i=1:5
        T = readtable([path num2str(micros) 'us_' num2str(i) '.csv']);
        toDelete = isnan(T.Wavelength_nm_);
        T(toDelete,:) = [];
        tableAggrevate = [tableAggrevate T.Intensity];
    end
    averagedTable = mean(tableAggrevate,2) % mean by row
    writematrix(averagedTable, [path num2str(micros) 'us_avg.csv'])
end