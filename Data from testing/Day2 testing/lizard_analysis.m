no_optics_intensities = csvread('lno/10000us_avg.csv');
optics_intensities = csvread('lo/10000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
ratio = (optics_intensities-3000)./(no_optics_intensities-3000);
plot(wavelength(70:300), ratio(70:300));
hold on;
