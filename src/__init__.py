
from  instance_manager    import InstanceManager

def main():
    i=InstanceManager.load_from_dat('./data/benchmark/medium/medium/MPVRP_M_001_s55_d4_p7.dat')
    for s in i.stations:
        print(sum(s.demand.values()))
        
main()
