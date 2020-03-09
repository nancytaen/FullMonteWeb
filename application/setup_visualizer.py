import paramiko, sys
import sshtunnel
from multiprocessing import Process
import os

# command = "pvpython -dr /opt/ParaView-5.7.0/share/paraview-5.7/web/visualizer/server/pvw-visualizer.py --paraview /opt/ParaView-5.7.0/ --data /home/Capstone/docker_sims/ --reverse-connect-port 8000"
port = int(os.environ.get("PORT", 4000))

def visualizer():

    with sshtunnel.open_tunnel(
        ("142.1.145.194", 9993),
        ssh_username="Capstone",
        ssh_password="pro929",
        remote_bind_address=('0.0.0.0',port),
        local_bind_address=('', 8080)
        ) as tunnel:

            print("Forwarding on " + str(port))
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

            while True:  # monitoring process
                # Reading from output streams
                while chan.recv_ready():
                    outdata += chan.recv(1000)
                while chan.recv_stderr_ready():
                    errdata += chan.recv_stderr(1000)
                if chan.exit_status_ready():  # If completed
                    break

            print(outdata)
            print(errdata)
            retcode = chan.recv_exit_status()
            ssh_transp.close()

def main():
    visualizer()

if __name__ == "__main__":
    main()
