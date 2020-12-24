#!/bin/env python3
import os
import datetime
import pymysql
from datetime import date
import array
import math
from os.path import expanduser

home = expanduser("~")
defaults_file = home + "/.my.cnf.slurm-aws"

dbcost = pymysql.connect(read_default_file=defaults_file)

cursorcost = dbcost.cursor()
cursoradd = dbcost.cursor()

# Read in the Amazon sizing into memory for future comparison
sql = "SELECT Instancetype, cores, mem, gpus, latestreservedcost, latestspotcost FROM Amazon ORDER BY latestreservedcost"
cursorcost.execute(sql)
amazon = []
while True:
    try:
        data=cursorcost.fetchone()
        amazon.append({"name":data[0], "cores":data[1], "mem":data[2], "gpus":data[3], "reservedcost":data[4], "spotcost":data[5]})
    except:
        break

sql = "SELECT a.jobid,a.runtime,a.cores,a.mem,a.nodes,a.gpus FROM jobinfo a NATURAL LEFT JOIN Amazonjobcost b WHERE b.jobid IS NULL ORDER BY a.jobid DESC"
cursorcost.execute(sql)
while True:
    try:
        data=cursorcost.fetchone()
        jobid=str(data[0])
        runtime=data[1]
        cores=data[2]
        mem=data[3]
        nodes=data[4]
        gpus=data[5]
        for row in amazon:
            if cores <= row['cores'] and mem <= row['mem'] and gpus <= row['gpus']:
                selectedrow=row
                break
# Costs in Amazon are in 100th's of cents per hour, so a value of 10000 would be $1/hr. We save this in cents per job. This is that conversion.
# We also assume that since an Amazon VCPU is half a core, it will take twice as long on Amazon as on Beocat.
# Take the cost / 100 to get cents/hr. Divide that by 3600 to get cents/second, and round up to the nearest penny. Save as a string since we're using it for string manipulation
        reservedcost=str(math.ceil(row['reservedcost']*runtime*nodes/360000))
        spotcost=str(math.ceil(row['spotcost']*runtime*nodes/360000))
        sql = "INSERT IGNORE INTO Amazonjobcost (jobid,instancetype,origreservedcost,origspotcost,latestreservedcost,latestspotcost) VALUES (" + jobid + ",'" + selectedrow['name'] + "'," + reservedcost + "," + spotcost + "," + reservedcost + "," + spotcost + ")"
        cursoradd.execute(sql)
        dbcost.commit()
    except:
        break

dbcost.close()