no_optics_intensities = csvread('icno/9000us_avg.csv');
optics_intensities = csvread('ico/15000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
ratio = (optics_intensities-3000)./(no_optics_intensities-3000);
plot(wavelength, ratio);
hold on;


no_optics_intensities = csvread('icno/7500us_avg.csv');
optics_intensities = csvread('ico/10000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
ratio = (optics_intensities-3000)./(no_optics_intensities-3000);
plot(wavelength, ratio);
hold on;

no_optics_intensities = csvread('icno/5000us_avg.csv');
optics_intensities = csvread('ico/7500us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
ratio = (optics_intensities-3000)./(no_optics_intensities-3000);
plot(wavelength, ratio);
hold on;

no_optics_intensities = csvread('icno/5000us_avg.csv');
optics_intensities = csvread('ico/5000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
ratio = (optics_intensities-3000)./(no_optics_intensities-3000);
plot(wavelength, ratio);
hold on;