#!/usr/bin/env python
from __future__ import division
import numpy    # for histogram stuff
import optparse
import os
import glob
import itertools
import random
import pickle    # for compressing the data not really needed right now
from collections import defaultdict
from IPython import parallel
import sys
import scipy
import string
from tables import *
import re
import time 


def grid_writer(job,value,final_grid,average_grid):
    name1 = job[0]
    id1 = job[1]
    name2 = job[2]
    id2 = job[3]
    shuffle = job[4]
    if shuffle:
        average_grid[id1-1][id2-1] += value
        if id1 != id2:
            average_grid[id2-1][id1-1] += value
    else:
        final_grid[id1-1][id2-1] += value
        if id1 != id2:
            final_grid[id2-1][id1-1] += value

def job_checker(dir,jobs,final_grid,average_grid):
    completed_jobs=[]
    if os.path.exists(dir+'temp-list.txt'):
        file=open(dir+'temp-list.txt','r')
        print "Previous Checkpoint Found:Pruning job list and writing out the matrix"
        for line in file:
      	#input  ('psi', 3, 'psi', 15, False)
            string=re.findall(r"\'[a-z,1-4]{3,4}\'\, \d+\, \'[a-z,1-4]{3,4}\', \d+\, [A-Z,a-z]{4,5}",line)
	    str_line='('+string[0]+')'
            for i,job in enumerate(jobs):
                if str_line == str(job[:5]):
                    print str_line 
		    print job[:5]
                    jobs.pop(i)
                    value=re.findall(r"[+-]?(\d+\.\d+([e][+-]\d+)?)",line)
                    print value[-1]
                    completed_jobs.append(job)
                    grid_writer(job,float(value[-1]),final_grid,average_grid)
                    
    return jobs     
            
        #do something
        


def create_hd5files_from_xvg(dir,skiprows):
    filename_list=glob.glob('%s*.xvg.all_data_450micro'%dir)
    for i,filename in enumerate(filename_list):
    #creating hdf5 files for those that have not been created before. 
        if not (os.path.exists(filename+'.h5')):
            h5file=openFile(filename+'.h5',"w",title="time")
            time_dihedral=h5file.createGroup("/",'time')
            data=numpy.loadtxt(filename,usecols=(1,),skiprows=skiprows)
            grid=h5file.createArray('/time','grid',data)
            h5file.close()
        


def timeit(method):

        def timed(*args, **kw):
                ts = time.time()
                result = method(*args, **kw)
                te = time.time()

                print 'Ran %r residue pairs in %2.2f sec' % \
                            (options.t, te-ts)
                return result

        return timed


def mutual_information_from_files(res_name1, res_id1, res_name2, res_id2,           shuffle, dir, skiprows,bin_n, test):

    #mutual_information_from_files
    """
    Contact: msultan at stanford dot edu

    The g-chi-mutinf.py utility is designed to calculate the mutual information between the dihedral angles of protein amino acid in an attempt to understand it mechanistic pathway
    Args:
        dir: the directory with the dihedral angles(with extension .xvg). This program is designed to work with the g-chi gromacs utility Please Make sure that the dihedral files are sequentially labelled(1-> total_n_residues)
        total_n_residues: The total number of residues. 
        n_iterations: How many items the data needs to be scrambled
        skiprows: The number of rows that need to be skipped in each .xvg file(eg g-chi out put has the first 12 rows as junk data) 
        bin_n: number of bins
        test: Boolean for testing the script
    Returns:
        Mutual Information
    """
    import numpy    #for histogram stuff
    import os
    import glob
    from scipy.stats.stats import pearsonr
    import tables
    import sys
    #creating a list with job in first column and result in 2nd column, this will be useful in restarting jobs
    job=(res_name1, res_id1, res_name2, res_id2,         shuffle, dir, skiprows,bin_n, test)    
    
    if not test:
        res_id1_range=[-180,180]
        res_id2_range=[-180,180]
        # example file namephiALA1.xvg.all_data_450micro
        #f.root.time_dihedral.grid[1]
        filename_id1 = glob.glob('%s%s???%d.xvg.all_data_450micro.h5' %(dir,res_name1,res_id1))
        print dir,res_name1,res_id1,filename_id1
	filename_id2 = glob.glob('%s%s???%d.xvg.all_data_450micro.h5' %(dir,res_name2,res_id2))
	if  filename_id1 and filename_id2:
       	    print "opening %s %s" %(filename_id1,filename_id2)
	    sys.stdout.flush()
            f=tables.openFile(filename_id1[0])
            dihedral_id1=numpy.array(f.root.time.grid[:])
            
            f=tables.openFile(filename_id2[0])
            dihedral_id2=numpy.array(f.root.time.grid[:])
            
            if shuffle:
                dihedral_id1 = numpy.random.permutation(dihedral_id1)
                dihedral_id2 = numpy.random.permutation(dihedral_id2)
        else:
            return job, 0.0
    if test:
        res_id1_range=[-3,3]
        res_id2_range=[-3,3]
        dihedral_id1 = numpy.random.normal(loc=0.0,scale=1.0,size=10000)
        dihedral_id2 = numpy.random.normal(loc=0.0,scale=1.0,size=10000)
#The magic begins here:The mutual information is defined as the 2d  sum of joint probability of x,y multiplied by the log(joint/marginal probabilites probabilities)

    
    (joint_pdf_bin_count,id1_bin_edges,id2_bin_edges) = numpy.histogram2d(dihedral_id1,dihedral_id2,bins=bin_n,range=[res_id1_range, res_id2_range],normed=False)
    
    dihedral_id1_count=numpy.sum(joint_pdf_bin_count,axis=0)
    dihedral_id2_count=numpy.sum(joint_pdf_bin_count,axis=1)
    
    dx=id1_bin_edges[1]-id1_bin_edges[0]
    N=len(dihedral_id1)
    H_x=-numpy.nansum((dihedral_id1_count/N) *numpy.log(dihedral_id1_count/N))+numpy.log(dx)
    H_y=-numpy.nansum((dihedral_id2_count/N) *numpy.log(dihedral_id2_count/N))+numpy.log(dx)
    H_x_y=-numpy.nansum((joint_pdf_bin_count/N) *numpy.log(joint_pdf_bin_count/N))+numpy.log(dx*dx)
    
    mutual=H_x+H_y-H_x_y
    
    if not test:
        return job,mutual

    if test:
        print "Variable                         Analytical           Calculated"
        print "H(x)                              ",(0.5*numpy.log(2*numpy.pi*numpy.e)), H_x
        print "H(y)                              ",(0.5*numpy.log(2*numpy.pi*numpy.e)), H_y
        det=numpy.linalg.det(numpy.cov(dihedral_id1,dihedral_id2))
        print "H(x,y)                            ",(0.5*numpy.log(det * (2*numpy.pi*numpy.e)**2)),H_x_y
        print "MI[H(x)+H(y)-H(x,y)]", ((0.5*numpy.log(2*numpy.pi*numpy.e))+(0.5*numpy.log(2*numpy.pi*numpy.e)) -(0.5*numpy.log(det * (2*numpy.pi*numpy.e)**2))),mutual

@timeit
def main(dir,total_n_residues,n_iterations,skiprows,bin_n, test):
    olderr = numpy.seterr(all='ignore') 
    #Setting up the parallel stuff 
    client_list=parallel.Client(profile='mpi')
    print "Running on:",len(client_list.ids)
    view = client_list.load_balanced_view()
    
    #dihedral names
    dihedral_names = ['chi1','chi2','chi3','chi4','phi','psi']
    
    #final job list. 
    jobs = []
    
    #grid
    
    #time_jump for saving results in seconds
    time_jump=1

    
    if test:
        print "TESTING BEGINNING:"
        mutual_information_from_files('junk',1,'junk',1,True,dir,skiprows,bin_n,True)
        print "TESTING FINISHED"
        sys.exit()
    else:
        final_grid = numpy.zeros(((total_n_residues),(total_n_residues)))
        average_grid = numpy.zeros(((total_n_residues),(total_n_residues)))
        print "Creating Job List"
        file_name_list=glob.glob('%s*.h5'%dir)
        print "Found",len(file_name_list),"files"
        for i,file_id1 in enumerate(file_name_list):
            name1=re.findall("chi1|chi2|chi3|chi4|phi|psi",file_name_list[i])[0]
            id1=int((re.findall("[A-Z]{3}\d+",file_name_list[i])[0])[3:])
            for j,file_id2 in enumerate(file_name_list[1020:]):
                name2=re.findall("chi1|chi2|chi3|chi4|phi|psi",file_name_list[j])[0]
                id2=int((re.findall("[A-Z]{3}\d+",file_name_list[j])[0])[3:])
                for ic in range(0,n_iterations):
                    if ic==0:
                        job=(name1, id1, name2, id2, False,dir,skiprows,bin_n,False)
                    else:
                        job = (name1, id1, name2, id2, True,dir,skiprows,bin_n,False)
                    jobs.append(job)
        print "Created",len(jobs),"jobs"
#       for id1 in range(1, total_n_residues+1):
#           for id2 in range(id1, total_n_residues+1):
#               for ic in range(0, n_iterations):
#                   for i, name1 in enumerate(dihedral_names):
#                       filename_id1 = glob.glob('%s%s???%d.*' %(dir,name1,id1))
#                       if filename_id1:
#                           for name2 in dihedral_names[i:]:
#                               filename_id2 = glob.glob('%s%s???%d.*'\ %(dir,name2,id2))
#                               if filename_id2:
#                                   if ic == 0:
#                                       job = (name1, id1, name2, id2, False,dir,skiprows,bin_n,False)
#                                   else:
#                                       job = (name1, id1, name2, id2, True,dir,skiprows,bin_n,False)
#                                   jobs.append(job)                            
    print "Pruning job list"
    jobs=job_checker(dir,jobs,final_grid,average_grid)
    if len(jobs)>0:
        st=time.time()
        print "Start the jobs with ", len(jobs),"jobs at",st
        result = view.map(mutual_information_from_files, *zip(*jobs),ordered=False,chunksize=1)

        print "Jobs Sent ;Waiting on Results Now"
        
        pending=set(result.msg_ids)
        
        #As long as there are pending jobs,
        #wait a while for the jobs to finish
        while pending:
            try:
                client_list.wait(pending,10)
	    except parallel.TimeoutError:
                pass
       	    #	print "Here" 
            finished=pending.difference(client_list.outstanding)
            pending=pending.difference(finished)

            for msg_id in finished:
            	print "here now"
		file=open('%s'%dir+'temp-list.txt','a')
                ar=client_list.get_result(msg_id)
		print ar.stdout
		for (job,mutual) in ar.result:
			print >> file, job,mutual
		file.close()
	
		print "BACKED UP THE DATA at %d"%(int(time.time()))
        
            
        all_mutuals = result.get()
        for i,job in enumerate(jobs):
            grid_writer(job,(all_mutuals[i])[1],final_grid,average_grid)
            
    final_grid=final_grid-(average_grid/n_iterations) 
    file=open('%s'%dir+'mut-inf-mat.txt', 'w')
    numpy.savetxt(file, final_grid)


def parse_commandline():
    parser = optparse.OptionParser()
    parser.add_option('-d', '--directory', dest='dir',default="../", help='directory with chi1,phi,psi files')
    parser.add_option('-t','--total_residues',dest='t',type="int",help='total       number of residues')
    parser.add_option('-i', '--total_iterations', dest='i', type="int", default=1, help=' total iterations')
    parser.add_option('--test', dest='test', default=0, help='test the code')
    parser.add_option('-s', '--skip_rows', dest='s',type='int', default=0,help='how many rows to skip')
    parser.add_option('-b', '--bins',dest='bin_n', type='int', default=24, help='The number of Bins used to bin data(Default 24). Too few bins can lead to problems')
    (options, args) = parser.parse_args()
    return (options, args)

#function main if namespace is main

if __name__ == "__main__":
    (options, args) = parse_commandline()
    create_hd5files_from_xvg(options.dir,options.s)
    main(dir=options.dir, total_n_residues=options.t,n_iterations=options.i,skiprows=options.s,bin_n=options.bin_n, test=options.test)
