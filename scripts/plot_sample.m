#!/usr/bin/octave -q
PAGER("/dev/null")

function disp(x)
end

arg_list = argv();
input = arg_list{1};

startindex = 0;
endindex = 3648;

wavelengths = dlmread(input,",",[startindex,0,endindex,0]);
intensities = dlmread(input,",",[startindex,1,endindex,1]);

sample = figure();
plot(wavelengths, intensities);
title(input);
xlabel("Wavelengths");
ylabel("Intensities");
xlim([300, 950]);
axis();

output = arg_list{2};
print(gcf,output,"-djpg");
