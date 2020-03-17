import paramiko, sys
from multiprocessing import Process

# command = "pvpython -dr /opt/ParaView-5.7.0/share/paraview-5.7/web/visualizer/server/pvw-visualizer.py --paraview /opt/ParaView-5.7.0/ --data /home/Capstone/docker_sims/ --reverse-connect-port 8000"

def visualizer():

    while True:
            # print("Forwarding on " + str(port))
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('142.1.145.194', port=9993, username='Capstone', password='pro929')
            ssh_transp = client.get_transport()

            chan = ssh_transp.open_session()
            # chan.settimeout(3 * 60 * 60)
            chan.setblocking(0)
            outdata, errdata = b'',b''

            chan.exec_command(command="Visualizer --paraview /opt/ParaView-5.7.0/ --data /home/Capstone/docker_sims/")

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
                return(retcode)
            #
            # except errExcept:
            #     while chan.recv_stderr_ready():
            #
            #     retcode = chan.recv_exit_status()
            #     ssh_transp.close()
            #     client.close()
            #
            #     print("Error encountered on remote server. Error message below:")
            #     print(errdata)

                # outData2 = b''
                #
                # chan.exec_command(command="sudo lsof -i:8080")
                #
                # outData2 += chan.recv(1000)
                # print(outData2)
                #

                # extract PID from error status message


if __name__ == "__main__":
    visualizer()
