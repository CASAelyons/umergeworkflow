#!/usr/bin/env python

import sys
import os
import pwd
import time
from Pegasus.DAX3 import *
from datetime import datetime
from argparse import ArgumentParser

class CASAWorkflow(object):
    def __init__(self, outdir, radar_files):
        self.outdir = outdir
        self.radar_files = radar_files

    def generate_dax(self):
        "Generate a workflow"
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        dax = ADAG("casa_wf-%s" % ts)
        dax.metadata("name", "CASA")
        #USER = pwd.getpwuid(os.getuid())[0]
        #dax.metadata("creator", "%s@%s" % (USER, os.uname()[1]))
        #dax.metadata("created", time.ctime())

        # unzip files if needed
        radar_inputs = []
        #last_time = "0"
        for f in self.radar_files:
            f = f.split("/")[-1]
            if f.endswith(".gz"):
                radar_input = f[:-3]
                radar_inputs.append(radar_input)

                unzip = Job("gunzip")
                unzip.addArguments(f)
                unzip.uses(f, link=Link.INPUT)
                unzip.uses(radar_input, link=Link.OUTPUT, transfer=False, register=False)
                dax.addJob(unzip)
            else:
                radar_inputs.append(f)
            #string_start = f.find("-")
            #string_end = f.find(".", string_start)
            #file_time = f[string_start+1:string_end]
            #if file_time > last_time:
            #    last_time = file_time
        
        string_start = self.radar_files[-1].find("-")
        string_end = self.radar_files[-1].find(".", string_start)
        last_time = self.radar_files[-1][string_start+1:string_end]

        #calculate max reflectivity (maybe split them to multiple ones)
        max_reflectivity = File("MaxReflectivity_"+last_time+".netcdf")
        ref_job = Job("UMerge_dynamo")
        ref_job.addArguments(" ".join(radar_inputs))
        for radar_input in radar_inputs:
            ref_job.uses(radar_input, link=Link.INPUT)
        ref_job.uses(max_reflectivity, link=Link.OUTPUT, transfer=True, register=False)
        dax.addJob(ref_job)

        # generate image from max reflectivity
        colorscale = File("nexrad_ref.png")
        max_reflectivity_image = File(max_reflectivity.name[:-7]+".png")
        post_ref_job = Job("merged_netcdf2png")
        post_ref_job.addArguments("-c", colorscale, "-q 235 -z 0,75", "-o", max_reflectivity_image, max_reflectivity)
        post_ref_job.uses(max_reflectivity, link=Link.INPUT)
        post_ref_job.uses(colorscale, link=Link.INPUT)
        post_ref_job.uses(max_reflectivity_image, link=Link.OUTPUT, transfer=True, register=False)
        dax.addJob(post_ref_job)

        # Write the DAX file
        daxfile = os.path.join(self.outdir, dax.name+".dax")
        dax.writeXMLFile(daxfile)
        print daxfile

    def generate_workflow(self):
        # Generate dax
        self.generate_dax()

if __name__ == '__main__':
    parser = ArgumentParser(description="CASA Workflow")
    parser.add_argument("-f", "--files", metavar="INPUT_FILES", type=str, nargs="+", help="Radar Files", required=True)
    parser.add_argument("-o", "--outdir", metavar="OUTPUT_LOCATION", type=str, help="DAX Directory", required=True)

    args = parser.parse_args()
    outdir = os.path.abspath(args.outdir)
    
    if not os.path.isdir(args.outdir):
        os.makedirs(outdir)

    workflow = CASAWorkflow(outdir, args.files)
    workflow.generate_workflow()
