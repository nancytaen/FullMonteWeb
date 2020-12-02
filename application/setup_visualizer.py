import paramiko, sys
from multiprocessing import Process

# def visualizer():
#     ph = ""
#     visualizer(ph)

def visualizer(args):
    cmd = "Visualizer --paraview /home/ubuntu/ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit/ --data /home/ubuntu/examples/"
    fileName = args

    # if (fileName):
    #     cmd += " --load-file " + fileName

    print(cmd)

    privkey = paramiko.RSAKey.from_private_key_file("/home/daixiao4/FullMonteWeb/application/LaunchUbuntuInstance.pem")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print ('connecting')
    
    client.connect(hostname='ec2-99-79-193-202.ca-central-1.compute.amazonaws.com', username='ubuntu', pkey=privkey)
    print ('connected')
    stdin, stdout, stderr = client.exec_command(cmd)
    stdout_line = stdout.readlines()
    stderr_line = stderr.readlines()
    for line in stdout_line:
        print (line)
    for line in stderr_line:
        print (line)

    print('finished')
    client.close()
    sys.stdout.flush()



if __name__ == "__main__":
    visualizer()
