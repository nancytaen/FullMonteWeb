from dataclasses import dataclass, asdict
from typing import Union

instances = []

ESTIMATED_TIME_KEY = 'time'
ESTIMATED_COST_KEY = 'cost'

CURRENCY = 'USD'
COST_FORMATTER_TEMPLATE = '$ {cost} {currency}'


@dataclass
class InstanceEstimate:
    time: str
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
        self.estimator = None
        self.ec2_type = ec2_type

    def _estimate_time(self, request):
        print(request)
        if self.estimator is None:
            return '00:08:29'

    def _estimate_cost(self, time):
        print(time)
        if self.estimator is None:
            return 0.051

    @staticmethod
    def format_cost(cost):
        return COST_FORMATTER_TEMPLATE.format(cost=cost, currency=CURRENCY)

    def estimate(self, request, format_cost=False):
        time = self._estimate_time(request)
        cost = self._estimate_cost(time)
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
