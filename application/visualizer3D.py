import paramiko, sys
import io
from multiprocessing import Process

# 3D interactive visualizer using ParaView Visualizer
def visualizer(meshFileName, fileExists, dns, tcpPort, text_obj):
    cmd = "Visualizer --paraview /home/ubuntu/ParaView-5.8.1-osmesa-MPI-Linux-Python2.7-64bit/ --data /home/ubuntu/docker_sims/ --port " + tcpPort

    if (fileExists):
        cmd += " --load-file " + meshFileName

    print(cmd)

    private_key_file = io.StringIO(text_obj)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privkey = paramiko.RSAKey.from_private_key(private_key_file)
    print ('connecting')
    client.connect(dns, username='ubuntu', pkey=privkey)
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
