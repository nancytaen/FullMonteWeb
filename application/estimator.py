from dataclasses import dataclass, asdict
from typing import Union
from pprint import pprint

instances = []

ESTIMATED_TIME_KEY = 'time'
ESTIMATED_COST_KEY = 'cost'

CURRENCY = 'USD'
COST_FORMATTER_TEMPLATE = '$ {cost} {currency}'

PACKET_COUNT_COEFF = 0.000005

class MaterialCoeffs:
    def __init__(self, scatteringCoeff, absorptionCoeff):
        self.scatteringCoeff = scatteringCoeff
        self.absorptionCoeff = absorptionCoeff


class InstanceInfo:
    def __init__(self, cost, vcpu, cpu_ram, instance_type, gpu):
        self.cost = cost
        self.vcpu = vcpu
        self.cpu_ram = cpu_ram
        self.instance_type = instance_type
        self.gpu = gpu

# @dataclass
# class InstanceInfo:
#     cost: float
#     vcpu: int
#     cpu_ram: Union[int, None] = None
#     type: str
#     gpu: Union[int, None] = None
#     gpu_ram: Union[int, None] = None

    

# TODO: Add gpu info
# TODO: Add other instances
instance_info = {
    "c5.4xlarge" : InstanceInfo(0.6800, 8, 32, "Instance_Type_Compute_Opti", 0),
    "c4.4xlarge" : InstanceInfo(0.7960, 8, 64, "Instance_Type_Compute_Opti", 0),
    "c5.9xlarge" : InstanceInfo(1.5300, 18, 32, "Instance_Type_Compute_Opti", 0),
    "t3a.2xlarge" : InstanceInfo(0.3008, 4, 32, "Instance_Type_General", 0),
    "t2.micro" : InstanceInfo(0.0104, 2, 1, "Instance_Type_General", 0),
    "t3.xlarge" : InstanceInfo(0.1664, 4, 16, "Instance_Type_General", 0),
    "t3.2xlarge" : InstanceInfo(0.3328, 8, 32, "Instance_Type_General", 0),
    "g4dn.xlarge" : InstanceInfo(0.526, 4, 16, "Instance_Type_General", 1)
}


@dataclass
class InstanceEstimate:
    time: float
    cost: float
    type: str
    vcpu: int
    gpu: Union[int, None] = None
    cpu_ram: Union[int, None] = None
    gpu_ram: Union[int, None] = None

    @staticmethod
    def _formatter(key, value):
        if key == 'cost':
            return TimeCostEstimator.format_cost(value)
        elif value is None:
            return 'n/a'
        else:
            return str(value)

    def dict(self):
        return {k: self._formatter(k, v) for k, v in asdict(self).items()}


class TimeCostEstimator:
    def __init__(self, ec2_stats, ec2_type):
        self.estimator = "decisionTree"
        self.ec2_type = ec2_type

    def _estimate_time(self, Mesh2_Scattering, Mesh2_Absor, Mesh3_Mu_Scattering, Mesh3_Mu_Absor, Mesh4_Mu_Scattering, Mesh4_Mu_Absor, Mesh5_Mu_Scattering, Mesh5_Mu_Absor, Mesh6_Mu_Scattering, Mesh6_Mu_Absor, Mesh7_Mu_Scattering, Mesh7_Mu_Absor, Mesh8_Mu_Scattering, Mesh8_Mu_Absor, Mesh9_Mu_Scattering, Mesh9_Mu_Absor, PacketCount , Storage, CPU_Cores, Instance_Type_Compute_Optimized, Instance_Type_General):
        if PacketCount  <= 550000000.0:
            if PacketCount  <= 55000000.0:
                if Mesh4_Mu_Absor <= 0.03:
                    if Mesh2_Scattering <= 6.4:
                        if Instance_Type_Compute_Optimized <= 0.5:
                            if Mesh5_Mu_Scattering <= 10.23:
                                return 74.235
                            else:  # if Mesh5_Mu_Scattering > 10.23
                                return 57.03
                        else:  # if Instance Type_Compute Optimized > 0.5
                            if Storage  <= 48.0:
                                if Storage <= 28.0:
                                    return 91.267
                                else:  # if Storage > 28.0
                                    return 91.247
                            else:  # if Storage > 48.0
                                return 306.349
                    else:  # if Mesh2_Scattering > 6.4
                        if CPU_Cores <= 13.0:
                            if Instance_Type_General <= 0.5:
                                if Storage <= 28.0:
                                    return 307.029
                                else:  # if Storage > 28.0
                                    return 620.01
                            else:  # if Instance_Type_General > 0.5
                                if Mesh2_Scattering <= 8.9:
                                    return 548.5435
                                else:  
                                    if Mesh4_Mu_Scattering <= 15.0:
                                        return 267.2335
                                    else:  # if Mesh4_Mu_Scattering > 15.0
                                        return 173.115
                        else:  # if CPU_Cores > 13.0
                            return 147.521
                else:  # if Mesh4_Mu_Absor > 0.03
                    if Storage <= 48.0:
                        if Mesh2_Absor <= 0.02:
                            return 2596.701
                        else:  # if Mesh2_Absor > 0.02
                            if Storage <= 28.0:
                                return 1115.885
                            else:  # if Storage > 28.0
                                return 972.916
                    else:  # if Storage > 48.0
                        if Mesh2_Scattering <= 17.8:
                            return 688.073
                        else:  # if Mesh2_Scattering > 17.8
                            return 71.69
            else:  # if PacketCount  > 55000000.0
                if CPU_Cores <= 6.0:
                    if Storage <= 48.0:
                        if Mesh5_Mu_Scattering <= 2.5:
                            return 2626.801
                        else:  # if Mesh5_Mu_Scattering > 2.5
                            if Mesh9_Mu_Scattering <= 5.52:
                                if Mesh5_Mu_Absor <= 0.02:
                                    return 1904.5075
                                else:  # if Mesh5_Mu_Absor > 0.02
                                    return 2041.284
                            else:  # if Mesh9_Mu_Scattering > 5.52
                                return 2252.5235
                    else:  # if Storage > 48.0
                        if Mesh3_Mu_Absor <= 0.0:
                            return 502.118
                        else:  # if Mesh3_Mu_Absor > 0.0
                            return 1405.032
                else:  # if CPU_Cores > 6.0
                    if Mesh3_Mu_Absor <= 0.0:
                        return 2111.556
                    else:  # if Mesh3_Mu_Absor > 0.0
                        if Mesh6_Mu_Absor <= 0.01:
                            return 972.916
                        else:  # if Mesh6_Mu_Absor > 0.01
                            if Mesh5_Mu_Scattering <= 61.35:
                                if Mesh5_Mu_Scattering <= 30.45:
                                    return 417.12166667
                                else:  # if Mesh5_Mu_Scattering > 30.45
                                    return 267.751
                            else:  # if Mesh5_Mu_Scattering > 61.35
                                return 79.438
        else:  # if PacketCount  > 550000000.0
            if Mesh5_Mu_Absor <= 0.12:
                if Mesh4_Mu_Absor <= 0.01:
                    return 30215.35
                else:  # if Mesh4_Mu_Absor > 0.01
                    if Mesh6_Mu_Scattering <= 4.5:
                        return 6642.233
                    else:  # if Mesh6_Mu_Scattering > 4.5
                        return 0.
            else:  # if Mesh5_Mu_Absor > 0.12
                return 69604.01
        final = return_val + PACKET_COUNT_COEFF*PacketCount # a higher packet count should linearly increase the time
        final = final * 0.9 if Instance_Type_Compute_Opti else final # If it's compute optimized, it should be faster
        return final

    def _estimate_cost(self, instance_specific_type, time):
        # print(time)
        if self.estimator is None:
            return 0.051
        else:
            return instance_info[instance_specific_type].cost * time / 360


    @staticmethod
    def format_cost(cost):
        return COST_FORMATTER_TEMPLATE.format(cost=cost, currency=CURRENCY)

    def estimate(self, request, instance, format_cost=False):

        materials = []
        for i in range(len(request.session['material'])):
            temp = MaterialCoeffs(request.session['scatteringCoeff'][i],request.session['absorptionCoeff'][i])
            # temp.scatteringCoeff = request.session['scatteringCoeff'][i]
            # temp.absorptionCoeff = request.session['absorptionCoeff'][i]
            materials.append(temp) 

        for i in range(len(request.session['material']),10):
            temp = MaterialCoeffs(0,0)
            materials.append(temp)


        # instance_type = request.session['ec2_instance_type']
        time = self._estimate_time(materials[1].scatteringCoeff, materials[1].absorptionCoeff, materials[2].scatteringCoeff, materials[2].absorptionCoeff,materials[3].scatteringCoeff, materials[3].absorptionCoeff, materials[4].scatteringCoeff, materials[4].absorptionCoeff, materials[5].scatteringCoeff, materials[5].absorptionCoeff, materials[6].scatteringCoeff, materials[6].absorptionCoeff, materials[7].scatteringCoeff, materials[7].absorptionCoeff, materials[8].scatteringCoeff, materials[8].absorptionCoeff, 
                                    request.session['packetCount'], instance_info[instance].cpu_ram, instance_info[instance].vcpu, instance_info[instance].instance_type == "Instance_Type_Compute_Opti", instance_info[instance].instance_type == "Instance_Type_General")
        cost = self._estimate_cost(instance, time)
        cost = round(cost,2) # Round the cost to 2 decimal points
        # return {
        #     time,
        #     self.format_cost(cost) if format_cost else cost,
        #     self.ec2_type
        # }
        return {
            ESTIMATED_TIME_KEY: time,
            ESTIMATED_COST_KEY: self.format_cost(cost) if format_cost else cost,
            'type': self.ec2_type
        }


class Recommendation:
    def __init__(self, request):
        self.request = request
        self.fastest = []
        self.cheapest = []

    def recommend(self):
        if self.request is None:
            return {
                'fastest': [
                    InstanceEstimate(
                        time='00:00:16',
                        cost=0.014,
                        type='p3.2xlarge',
                        vcpu=8,
                        gpu=1,
                        gpu_ram=16,
                    ).dict(),
                    InstanceEstimate(
                        time='00:00:24',
                        cost=0.057,
                        type='g4dn.2xlarge',
                        vcpu=8,
                        gpu=1,
                        cpu_ram=32,
                        gpu_ram=16
                    ).dict()
                ],
                'cheapest': [
                    InstanceEstimate(
                        time='00:11:27',
                        cost=0.005,
                        type='t3a.2xlarge',
                        vcpu=8,
                        cpu_ram=32
                    ).dict(),
                    InstanceEstimate(
                        time='00:00:16',
                        cost=0.014,
                        type='p3.2xlarge',
                        vcpu=8,
                        gpu=1,
                        gpu_ram=16,
                    ).dict(),
                ]
            }
        else:
            # Run the Estimator with all the different instance parameters and save the three cheapest and fastests
            estimated_instances = []
            for instance in instance_info:
                # time, cost, type = TimeCostEstimator(None, self.request.session['ec2_instance_type']).estimate(self.request, format_cost=True)
                result = TimeCostEstimator(None, instance).estimate(self.request, instance, format_cost=False)
                estimated_instances.append(InstanceEstimate(
                        time=result[ESTIMATED_TIME_KEY],
                        cost=result[ESTIMATED_COST_KEY],
                        type=result['type'],
                        vcpu=instance_info[instance].vcpu,
                        cpu_ram=instance_info[instance].cpu_ram 
                    ).dict()
                )

                
            sorted_time = sorted(estimated_instances, key=lambda inst: float(inst['time']))
            sorted_cost = sorted(estimated_instances, key=lambda inst: inst['cost'])

            return {
                'fastest': sorted_time[0:3],
                'cheapest': sorted_cost[0:3],
            }




# if __name__ == "__main__":
#     recc = Recommendation(None)
#     pprint(recc.recommend())
#     sorted_products = sorted(recc.recommend()['cheapest'], key=lambda instance: instance['time'], reverse = True)
#     pprint(sorted_products[0:3])