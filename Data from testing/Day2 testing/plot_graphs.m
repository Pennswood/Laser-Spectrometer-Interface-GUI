no_optics_intensities = csvread('icno/9000us_avg.csv');
optics_intensities = csvread('ico/15000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
plot(wavelength, no_optics_intensities./60000,'.');
plot(wavelength, optics_intensities./60000,'.');
hold on;

no_optics_intensities = csvread('lno/10000us_avg.csv');
optics_intensities = csvread('lo/10000us_avg.csv');
wavelength = readtable('wavelength_chart.csv').Var1;
plot(wavelength, no_optics_intensities./60000,'.');
plot(wavelength, optics_intensities./60000,'.');
hold on;
