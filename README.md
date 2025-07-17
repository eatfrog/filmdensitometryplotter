Example:

densitometer_plot.py -ev 0.8 -t 0.5 -s .\stouffer.csv -f .\kentmere200-2.csv -n "Kentmere 200" -d 0.30

   * -ev (float, required): The Exposure Value (EV).
   * -t or --exposure_time (float, required): The exposure time in seconds.
   * -s or --step_wedge (string, required): The path to the CSV file containing the step wedge density measurements.
   * -f or --film (string, required): The path to the CSV file containing the test film density measurements.
   * -n or --name (string, required): The name of the test film.
   * -d or --dmin (float, required): The minimum density (Dmin) of the film.
   * -dx or --dmax (float, optional): The maximum density (Dmax) of the film.
