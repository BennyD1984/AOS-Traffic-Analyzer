# AOS-Traffic-Analyzer
Simple traffic analyzer for Alcatel-Lucent OmniSwitches, giving clear view on interface traffic stats with SSH.

![Image description].(AOS-Traffic-Analyzer-Screenshot.png)

You need to install paramiko and prettytable to run the script. 

Simply run the script with: "python AOS-Traffic-Analyzer-v1_3.py 192.168.1.254 [username] -p [password] 

You need to install getpass, if you don´t want to type password in cleartext. You will then get requested to enter password after launching the script. 

Optional paramters are:

-r [number]      Increase the number of measurements.

-t [number]      Set a trending view. How many of last measurements you want to see.

-i [number]      Intervall of measurements multiplied by 5. Default is 1, so every 5 secons one measurement.

-pc [number]     Pause between commands. Increase if the results seem to be incomplete. Default 0.5 seconds.

Known issues not yet fixed:
- The first value of BUM traffic is shown as absolute value, not relative. This is due to missing compare value in first recording.
- The script only checks active port at the start of the script. If an interface goes down during runtime, it shows the values from the   next active port that the RegEx matches. If an interface goes up during runtime of the script, it won´t be considered in the results.

