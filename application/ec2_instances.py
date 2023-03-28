class EC2InstanceStats:
    def __init__(self, client):
        self.ec2_type = None
        self.cpu_size = None
        self.disk_size = None
        self.client = client

    def get_current_ec2_instance_type(self):
        stdin, stdout, stderr = self.client.exec_command('curl http://169.254.169.254/latest/meta-data/instance-type')
        stdout_line = stdout.readlines()
        stderr_line = stderr.readlines()
        for line in stderr_line:
            print(line)
        for line in stdout_line:
            return line
