import shortuuid


class ServerlessParameters:
    SERVERLESS_REQUEST = 'serverless_request'
    ID = 'request_id'
    MESH = 'mesh_name'
    TCL = 'tcl_name'
    BASE = 'base_name'

    def __init__(self, mesh_name):
        self.request_id = shortuuid.uuid()
        self.mesh_name = self.insert_id_to_filename(mesh_name)
        self.base_name = self.get_base(self.mesh_name)
        self.tcl_name = f'{self.base_name}tcl'

    def insert_id_to_filename(self, filename):
        # split filename into basename and extension
        # basename-<request_id>.ext
        partitions = filename.rsplit('.', 1)
        return f'{partitions[0].replace(".", "-")}-{self.request_id}.{partitions[1]}'

    @staticmethod
    def extract_id_from_filename(filename):
        # use - and . as delimiters to extract the request id from filename
        base = filename.rsplit('.', 1)[0]
        return base.rsplit('-', 1)[1]

    @staticmethod
    def get_base(mesh_name):
        # base name includes . e.g. something.vtk -> something.
        return mesh_name[:-3]
