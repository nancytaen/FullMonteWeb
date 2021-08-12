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
    print ('>>> connecting to remote server in visualizer3D...')
    client.connect(dns, username='ubuntu', pkey=privkey)
    try:
        print ('>>> connected to remote server in visualizer3D.')

        # kill any existing processes running on tcpPort
        print("sudo kill -9 `sudo lsof -t -i:" + tcpPort + "`")
        stdin, stdout, stderr = client.exec_command("sudo kill -9 `sudo lsof -t -i:" + tcpPort + "`")
        stdout_line = stdout.readlines()
        stderr_line = stderr.readlines()
        for line in stdout_line:
            print (line)
        for line in stderr_line:
            print (line)
        sys.stdout.flush()


        # set channel
        ssh_transp = client.get_transport()
        chan = ssh_transp.open_session()
        chan.setblocking(0)
        outdata, errdata = b'',b''

        chan.exec_command(command=cmd)    

        try:
            while True:  # monitoring process
                # Reading from output streams
                while chan.recv_ready():
                    outdata += chan.recv(1000)
                if chan.recv_stderr_ready():
                    errdata += chan.recv_stderr(1000)
                if chan.exit_status_ready():  # If completed
                    break

            print(outdata)
            print(errdata)

        finally:
            retcode = chan.recv_exit_status()
            ssh_transp.close()
            client.close()

            print("Visualizer process exited with code " + str(retcode))
            return(retcode)
    finally:
        client.close()
        print ('>>> destroyed connection from remote server in visualizer3D.')


if __name__ == "__main__":
    visualizer()
