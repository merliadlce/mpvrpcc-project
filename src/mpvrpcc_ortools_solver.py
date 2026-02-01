# -*- coding: utf-8 -*-
"""
Multi-Product Vehicle Routing Problem with Changeover Cost (MPVRP-CC)
Solveur utilisant Google OR-Tools comme moteur d'optimisation

Modèle mathématique :
- Minimiser : Coût_distance + Coût_changements_produit
- Contraintes : 
  * Satisfaction demandes
  * Capacité véhicules
  * Conservation flux
  * Changements de produit avec coûts
"""

import time
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Set, Optional
from collections import defaultdict

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import platform

import numpy as np


class LocationType:
    """Types de localisation"""
    GARAGE = "garage"
    DEPOT = "depot"
    STATION = "station"


@dataclass
class Location:
    """Représente un lieu dans le réseau logistique"""
    id: int
    x: float
    y: float
    name: str = ""
    

@dataclass
class Truck:
    """Camion avec capacité et garage d'attache"""
    id: int
    capacity: float
    garage_id: int
    initial_product: int = 0


@dataclass
class Depot:
    """Dépôt avec stocks par produit"""
    id: int
    location: Location
    stock: Dict[int, float]


@dataclass
class Station:
    """Station service avec demandes par produit"""
    id: int
    location: Location
    demand: Dict[int, float]


@dataclass
class MiniRoute:
    """Mini-route : Dépôt -> [Stations] pour un produit"""
    depot_id: int
    product_id: int
    load_quantity: float
    stations: List[Tuple[int, float]]


@dataclass
class CompleteRoute:
    """Route complète d'un camion : Garage -> [Mini-routes] -> Garage"""
    truck_id: int
    garage_id: int
    mini_routes: List[MiniRoute]
    total_distance: float = 0.0
    total_changeover_cost: float = 0.0
    total_cost: float = 0.0


class MPVRPCCInstance:
    """Instance du problème MPVRP-CC"""
    
    def __init__(self, name: str = "instance"):
        self.name = name
        self.garages: List[Location] = []
        self.depots: List[Depot] = []
        self.stations: List[Station] = []
        self.trucks: List[Truck] = []
        
        self.products: Set[int] = set()
        self.changeover_costs: Dict[Tuple[int, int], float] = {}
        self.distance_matrix: Dict[Tuple[str, int, str, int], float] = {}
        
    def add_garage(self, x: float, y: float, name: str = "") -> int:
        """Ajoute un garage"""
        garage_id = len(self.garages) + 1
        self.garages.append(Location(garage_id, x, y, name or f"Garage_{garage_id}"))
        return garage_id
        
    def add_depot(self, x: float, y: float, stock: Dict[int, float], name: str = "") -> int:
        """Ajoute un dépôt avec stocks par produit"""
        depot_id = len(self.depots) + 1
        location = Location(depot_id, x, y, name or f"Depot_{depot_id}")
        self.depots.append(Depot(depot_id, location, stock))
        self.products.update(stock.keys())
        return depot_id
        
    def add_station(self, x: float, y: float, demand: Dict[int, float], name: str = "") -> int:
        """Ajoute une station avec demandes par produit"""
        station_id = len(self.stations) + 1
        location = Location(station_id, x, y, name or f"Station_{station_id}")
        self.stations.append(Station(station_id, location, demand))
        self.products.update(demand.keys())
        return station_id
        
    def add_truck(self, capacity: float, garage_id: int, initial_product: int = 0) -> int:
        """Ajoute un camion"""
        truck_id = len(self.trucks) + 1
        self.trucks.append(Truck(truck_id, capacity, garage_id, initial_product))
        return truck_id
        
    def set_changeover_costs(self, costs: Dict[Tuple[int, int], float]):
        """Définit les coûts de changement de produit"""
        self.changeover_costs = costs
        
    def get_changeover_cost(self, from_product: int, to_product: int) -> float:
        """Retourne le coût de changement entre deux produits"""
        if from_product == to_product:
            return 0.0
        return self.changeover_costs.get((from_product, to_product), 0.0)
        
    def distance(self, loc_type1: str, id1: int, loc_type2: str, id2: int) -> float:
        """Calcule la distance euclidienne entre deux lieux"""
        key = (loc_type1, id1, loc_type2, id2)
        if key in self.distance_matrix:
            return self.distance_matrix[key]
            
        loc1 = self._get_location(loc_type1, id1)
        loc2 = self._get_location(loc_type2, id2)
        
        dist = math.sqrt((loc1.x - loc2.x)**2 + (loc1.y - loc2.y)**2)
        
        self.distance_matrix[key] = dist
        self.distance_matrix[(loc_type2, id2, loc_type1, id1)] = dist
        
        return dist
        
    def _get_location(self, loc_type: str, loc_id: int) -> Location:
        """Récupère un objet Location"""
        if loc_type == LocationType.GARAGE:
            return next(g for g in self.garages if g.id == loc_id)
        elif loc_type == LocationType.DEPOT:
            return next(d.location for d in self.depots if d.id == loc_id)
        elif loc_type == LocationType.STATION:
            return next(s.location for s in self.stations if s.id == loc_id)
        else:
            raise ValueError(f"Type de location inconnu: {loc_type}")
    
    def get_total_demand(self) -> Dict[int, float]:
        """Retourne la demande totale par produit"""
        total = defaultdict(float)
        for station in self.stations:
            for product, qty in station.demand.items():
                total[product] += qty
        return dict(total)
    
    def validate_instance(self) -> Tuple[bool, List[str]]:
        """Valide la cohérence de l'instance"""
        errors = []
        
        if not self.garages:
            errors.append("Aucun garage défini")
        if not self.depots:
            errors.append("Aucun dépôt défini")
        if not self.stations:
            errors.append("Aucune station définie")
        if not self.trucks:
            errors.append("Aucun camion défini")
            
        total_demand = self.get_total_demand()
        for product in total_demand:
            total_stock = sum(d.stock.get(product, 0) for d in self.depots)
            if total_stock < total_demand[product]:
                errors.append(f"Stock insuffisant pour produit {product}: {total_stock} < {total_demand[product]}")
        
        total_capacity = sum(t.capacity for t in self.trucks)
        max_demand = max(total_demand.values()) if total_demand else 0
        if total_capacity < max_demand:
            errors.append(f"Capacité totale insuffisante: {total_capacity} < {max_demand}")
            
        return len(errors) == 0, errors


class MPVRPCCORToolsSolver:
    """
    Solveur MPVRP-CC utilisant OR-Tools
    Stratégie : décomposition produit-par-produit avec optimisation par VRP
    """
    
    def __init__(self, instance: MPVRPCCInstance):
        self.instance = instance
        self.solution: List[CompleteRoute] = []
        self.start_time = None
        self.end_time = None
        self.total_cost = 0.0
        
    def solve(self, time_limit: int = 60, verbose: bool = True) -> List[CompleteRoute]:
        """
        Résout le problème MPVRP-CC avec OR-Tools
        
        Args:
            time_limit: Temps limite en secondes
            verbose: Afficher les logs
            
        Returns:
            Liste des routes complètes
        """
        self.start_time = time.time()
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"Résolution MPVRP-CC avec OR-Tools - Instance: {self.instance.name}")
            print(f"{'='*70}")
            print(f"Camions: {len(self.instance.trucks)}")
            print(f"Dépôts: {len(self.instance.depots)}")
            print(f"Stations: {len(self.instance.stations)}")
            print(f"Produits: {len(self.instance.products)}")
        
        # Stratégie de décomposition : traiter produit par produit
        self.solution = self._solve_product_by_product(time_limit, verbose)
        
        self.end_time = time.time()
        
        if verbose:
            print(f"\n✓ Solution trouvée en {self.end_time - self.start_time:.3f}s")
        
        return self.solution
    
    def _solve_product_by_product(
        self, 
        time_limit: float, 
        verbose: bool
    ) -> List[CompleteRoute]:
        """
        Décompose le problème par produit et résout avec OR-Tools
        """
        routes = []
        used_trucks = set()
        remaining_demand = self._initialize_remaining_demand()
        
        for product in sorted(self.instance.products):
            if verbose:
                print(f"\n[Produit {product}] Optimisation VRP...")
            
            # Stations ayant besoin de ce produit
            stations_needing = [
                s for s in self.instance.stations
                if remaining_demand.get((s.id, product), 0) > 0
            ]
            
            if not stations_needing:
                continue
            
            # Dépôts fournissant ce produit
            depots_supplying = [
                d for d in self.instance.depots
                if d.stock.get(product, 0) > 0
            ]
            
            if not depots_supplying:
                continue
            
            # Résoudre le VRP pour ce produit avec OR-Tools
            product_routes = self._solve_vrp_for_product_ortools(
                product, 
                stations_needing, 
                depots_supplying,
                remaining_demand,
                used_trucks,
                time_limit,
                verbose
            )
            
            routes.extend(product_routes)
            
            # Mettre à jour les demandes
            for route in product_routes:
                for mini_route in route.mini_routes:
                    for station_id, qty in mini_route.stations:
                        remaining_demand[(station_id, product)] -= qty
            
            # Remarque: on autorise la réutilisation des camions pour d'autres produits
        
        return routes
    
    def _solve_vrp_for_product_ortools(
        self,
        product: int,
        stations: List[Station],
        depots: List[Depot],
        remaining_demand: Dict[Tuple[int, int], float],
        used_trucks: Set[int],
        time_limit: float,
        verbose: bool
    ) -> List[CompleteRoute]:
        """
        Résout un VRP pour un produit donné avec OR-Tools
        """
        # Sélectionner les camions disponibles
        available_trucks = [
            t for t in self.instance.trucks
            if t.id not in used_trucks
        ]
        
        if not available_trucks:
            return []
        
        depot = depots[0]
        routes = []
        
        # Créer le modèle OR-Tools
        manager = pywrapcp.RoutingIndexManager(
            len(stations) + 1,  # +1 pour le dépôt
            len(available_trucks),
            0  # index du dépôt
        )
        
        routing = pywrapcp.RoutingModel(manager)
        
        # Callback de distance
        def distance_callback(from_idx, to_idx):
            from_node = manager.IndexToNode(from_idx)
            to_node = manager.IndexToNode(to_idx)
            
            if from_node == 0:  # Depuis le dépôt
                if to_node == 0:
                    return 0
                station = stations[to_node - 1]
                return int(self.instance.distance(
                    LocationType.DEPOT, depot.id,
                    LocationType.STATION, station.id
                ) * 1000)  # Conversion en entiers
            elif to_node == 0:  # Vers le dépôt
                station = stations[from_node - 1]
                return int(self.instance.distance(
                    LocationType.STATION, station.id,
                    LocationType.DEPOT, depot.id
                ) * 1000)
            else:  # Entre stations
                from_station = stations[from_node - 1]
                to_station = stations[to_node - 1]
                return int(self.instance.distance(
                    LocationType.STATION, from_station.id,
                    LocationType.STATION, to_station.id
                ) * 1000)
        
        distance_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

        # Callback de demande (capacité)
        def demand_callback(from_idx):
            from_node = manager.IndexToNode(from_idx)
            if from_node == 0:
                return 0
            station = stations[from_node - 1]
            return int(remaining_demand.get((station.id, product), 0) * 100)  # Conversion

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        # Ajouter la dimension capacité (par véhicule)
        vehicle_capacities = [int(t.capacity * 100) for t in available_trucks]
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # slack_max
            vehicle_capacities,
            True,
            "Capacity"
        )

        # Paramètres de recherche
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = int(time_limit * 0.5)

        # Résoudre
        solution = routing.SolveWithParameters(search_parameters)

        if not solution:
            # Fallback : utiliser greedy
            return self._assign_stations_greedy(
                product, stations, available_trucks,
                depot, remaining_demand
            )

        # Extraire la solution standard OR-Tools
        for vehicle_id in range(len(available_trucks)):
            truck = available_trucks[vehicle_id]
            index = routing.Start(vehicle_id)
            station_list = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                # node == 0 correspond au dépôt
                if node != 0:
                    # node-1 est l'index dans la liste stations
                    station = stations[node - 1]
                    station_list.append(station)
                index = solution.Value(routing.NextVar(index))

            if station_list:
                route = self._build_complete_route(
                    truck, depot, product, station_list, remaining_demand
                )
                if route and route.mini_routes:
                    routes.append(route)
        
        return routes
    
    def _assign_stations_greedy(
        self,
        product: int,
        stations: List[Station],
        trucks: List[Truck],
        depot: Depot,
        remaining_demand: Dict[Tuple[int, int], float]
    ) -> List[CompleteRoute]:
        """Fallback: assigne les stations aux camions via greedy nearest-neighbor"""
        truck_routes = {t.id: [] for t in trucks}
        truck_load = {t.id: 0.0 for t in trucks}
        unvisited = set(s.id for s in stations)
        
        while unvisited:
            best_assignment = None
            best_cost = float('inf')
            
            for station_id in list(unvisited):
                station = next(s for s in stations if s.id == station_id)
                demand = remaining_demand.get((station.id, product), 0)
                
                if demand <= 0:
                    unvisited.remove(station_id)
                    continue
                
                for truck in trucks:
                    if truck_load[truck.id] + demand <= truck.capacity:
                        distance_cost = self.instance.distance(
                            LocationType.DEPOT, depot.id,
                            LocationType.STATION, station.id
                        )
                        
                        if distance_cost < best_cost:
                            best_cost = distance_cost
                            best_assignment = (truck.id, station)
            
            if best_assignment:
                truck_id, station = best_assignment
                truck_routes[truck_id].append(station)
                demand = remaining_demand.get((station.id, product), 0)
                truck_load[truck_id] += demand
                unvisited.remove(station.id)
            else:
                break
        
        routes = []
        for truck in trucks:
            if truck_routes[truck.id]:
                route = self._build_complete_route(
                    truck, depot, product,
                    truck_routes[truck.id],
                    remaining_demand
                )
                if route and route.mini_routes:
                    routes.append(route)
        
        return routes
    
    def _build_complete_route(
        self,
        truck: Truck,
        depot: Depot,
        product: int,
        stations: List[Station],
        remaining_demand: Dict[Tuple[int, int], float]
    ) -> Optional[CompleteRoute]:
        """Construit une route complète pour un camion"""
        route = CompleteRoute(truck.id, truck.garage_id, [])
        
        mini_route = self._build_mini_route(
            truck, depot, product, stations, remaining_demand
        )
        
        if mini_route:
            route.mini_routes.append(mini_route)
            route.total_distance = self._calculate_route_distance(route)
            route.total_changeover_cost = self._calculate_changeover_cost(route, truck)
            route.total_cost = route.total_distance + route.total_changeover_cost
        
        return route
    
    def _build_mini_route(
        self,
        truck: Truck,
        depot: Depot,
        product: int,
        stations: List[Station],
        remaining_demand: Dict[Tuple[int, int], float]
    ) -> Optional[MiniRoute]:
        """Construit une mini-route pour un produit"""
        total_demand = sum(
            remaining_demand.get((s.id, product), 0)
            for s in stations
        )
        
        load_quantity = min(
            truck.capacity,
            total_demand,
            depot.stock.get(product, 0)
        )
        
        if load_quantity <= 0:
            return None
        
        # Optimiser la séquence avec nearest-neighbor
        stations_to_serve = []
        remaining_capacity = load_quantity
        unvisited = stations.copy()
        
        while unvisited and remaining_capacity > 0:
            nearest = min(
                unvisited,
                key=lambda s: self.instance.distance(
                    LocationType.DEPOT, depot.id,
                    LocationType.STATION, s.id
                )
            )
            
            demand = remaining_demand.get((nearest.id, product), 0)
            delivery_qty = min(remaining_capacity, demand)
            
            if delivery_qty > 0:
                stations_to_serve.append((nearest.id, delivery_qty))
                remaining_capacity -= delivery_qty
            
            unvisited.remove(nearest)
        
        if not stations_to_serve:
            return None
        
        return MiniRoute(
            depot_id=depot.id,
            product_id=product,
            load_quantity=load_quantity,
            stations=stations_to_serve
        )
    
    def _calculate_route_distance(self, route: CompleteRoute) -> float:
        """Calcule la distance totale d'une route"""
        total_distance = 0.0
        garage = next(g for g in self.instance.garages if g.id == route.garage_id)
        
        if not route.mini_routes:
            return 0.0
        
        # Garage -> premier dépôt
        first_depot_id = route.mini_routes[0].depot_id
        total_distance += self.instance.distance(
            LocationType.GARAGE, garage.id,
            LocationType.DEPOT, first_depot_id
        )
        
        prev_type, prev_id = LocationType.DEPOT, first_depot_id
        
        for mini_route in route.mini_routes:
            # Distance vers le dépôt
            if prev_type != LocationType.DEPOT or prev_id != mini_route.depot_id:
                total_distance += self.instance.distance(
                    prev_type, prev_id,
                    LocationType.DEPOT, mini_route.depot_id
                )
            
            prev_type, prev_id = LocationType.DEPOT, mini_route.depot_id
            
            # Distances vers les stations
            for station_id, _ in mini_route.stations:
                total_distance += self.instance.distance(
                    prev_type, prev_id,
                    LocationType.STATION, station_id
                )
                prev_type, prev_id = LocationType.STATION, station_id
        
        # Dernière station -> garage
        total_distance += self.instance.distance(
            prev_type, prev_id,
            LocationType.GARAGE, garage.id
        )
        
        return total_distance
    
    def _calculate_changeover_cost(self, route: CompleteRoute, truck: Truck) -> float:
        """Calcule les coûts de changement de produit"""
        total_cost = 0.0
        current_product = truck.initial_product
        
        for mini_route in route.mini_routes:
            if current_product != mini_route.product_id:
                total_cost += self.instance.get_changeover_cost(
                    current_product, mini_route.product_id
                )
                current_product = mini_route.product_id
        
        return total_cost
    
    def _initialize_remaining_demand(self) -> Dict[Tuple[int, int], float]:
        """Initialise les demandes restantes"""
        remaining = {}
        for station in self.instance.stations:
            for product, qty in station.demand.items():
                remaining[(station.id, product)] = qty
        return remaining
    
    def get_metrics(self) -> Dict:
        """Calcule les métriques de la solution"""
        total_distance = sum(r.total_distance for r in self.solution)
        total_changeover = sum(r.total_changeover_cost for r in self.solution)
        
        num_changes = 0
        for route in self.solution:
            for i in range(1, len(route.mini_routes)):
                if route.mini_routes[i].product_id != route.mini_routes[i-1].product_id:
                    num_changes += 1
        
        return {
            'num_vehicles': len(set(r.truck_id for r in self.solution)),
            'num_product_changes': num_changes,
            'total_changeover_cost': total_changeover,
            'total_distance': total_distance,
            'computation_time': self.end_time - self.start_time if self.end_time else 0,
            'total_cost': total_distance + total_changeover
        }
    
    def validate_solution(self) -> Tuple[bool, List[str]]:
        """Valide que la solution respecte toutes les contraintes"""
        errors = []
        
        # Vérifier que toutes les demandes sont satisfaites
        delivered = defaultdict(float)
        for route in self.solution:
            for mini_route in route.mini_routes:
                for station_id, qty in mini_route.stations:
                    delivered[(station_id, mini_route.product_id)] += qty
        
        for station in self.instance.stations:
            for product, demand in station.demand.items():
                delivered_qty = delivered.get((station.id, product), 0)
                if abs(delivered_qty - demand) > 0.01:
                    errors.append(
                        f"Demande non satisfaite Station {station.id} Produit {product}: "
                        f"{delivered_qty} ≠ {demand}"
                    )
        
        # Vérifier la capacité des camions
        for route in self.solution:
            truck = next(t for t in self.instance.trucks if t.id == route.truck_id)
            for mini_route in route.mini_routes:
                if mini_route.load_quantity > truck.capacity:
                    errors.append(
                        f"Capacité dépassée Camion {truck.id}: "
                        f"{mini_route.load_quantity} > {truck.capacity}"
                    )
        
        return len(errors) == 0, errors


class SolutionFormatter:
    """Formate et exporte la solution"""
    
    @staticmethod
    def write_solution(
        instance: MPVRPCCInstance,
        solution: List[CompleteRoute],
        metrics: Dict,
        filename: str
    ):
        """Écrit la solution au format .dat"""
        with open(filename, 'w', encoding='utf-8') as f:
            for route in solution:
                SolutionFormatter._write_route(f, instance, route)
            
            # Métriques finales
            f.write(f"{metrics['num_vehicles']}\n")
            f.write(f"{metrics['num_product_changes']}\n")
            f.write(f"{metrics['total_changeover_cost']:.2f}\n")
            f.write(f"{metrics['total_distance']:.2f}\n")
            
            # Info processeur
            try:
                processor = platform.processor()
            except:
                processor = "Unknown"
            f.write(f"{processor}\n")
            
            # Temps de génération
            f.write(f"{metrics['computation_time']:.3f}\n")

    @staticmethod
    def _write_route(f, instance: MPVRPCCInstance, route: CompleteRoute):
        """Écrit une route complète (2 lignes + ligne vide)"""
        truck = next(t for t in instance.trucks if t.id == route.truck_id)
        garage_id = truck.garage_id
        
        visit_sequence = [str(garage_id)]
        product_sequence = []
        cumulative_changeover = 0.0
        current_product = truck.initial_product
        
        for mini_route in route.mini_routes:
            if current_product != mini_route.product_id:
                cumulative_changeover += instance.get_changeover_cost(
                    current_product, mini_route.product_id
                )
                current_product = mini_route.product_id
            
            # Ajouter le dépôt avec sa charge
            load_int = int(mini_route.load_quantity)
            visit_sequence.append(f"{mini_route.depot_id} [{load_int}]")
            product_sequence.append(f"{current_product}({cumulative_changeover:.1f})")
            
            for station_id, delivery_quantity in mini_route.stations:
                delivery_int = int(delivery_quantity)
                visit_sequence.append(f"{station_id} ({delivery_int})")
                product_sequence.append(f"{current_product}({cumulative_changeover:.1f})")
        
        visit_sequence.append(str(garage_id))
        product_sequence.append(f"{current_product}({cumulative_changeover:.1f})")
        
        f.write(f"{route.truck_id}: " + " - ".join(visit_sequence) + "\n")
        f.write(f"{route.truck_id}: " + " - ".join(product_sequence) + "\n")
        f.write("\n")
    
    @staticmethod
    def print_solution(instance: MPVRPCCInstance, solution: List[CompleteRoute], metrics: Dict):
        """Affiche la solution de manière lisible"""
        print(f"\n{'='*70}")
        print(f"SOLUTION MPVRP-CC - {instance.name}")
        print(f"{'='*70}")
        
        for route in solution:
            truck = next(t for t in instance.trucks if t.id == route.truck_id)
            print(f"\nCamion {route.truck_id} (Garage {truck.garage_id}):")
            print(f"  Distance: {route.total_distance:.2f} km")
            print(f"  Coût changements: {route.total_changeover_cost:.2f}")
            print(f"  Coût total: {route.total_cost:.2f}")
            
            for i, mini_route in enumerate(route.mini_routes, 1):
                print(f"  Mini-route {i}: Produit {mini_route.product_id}, "
                      f"Charge {mini_route.load_quantity:.2f} ({len(mini_route.stations)} stations)")
        
        print(f"\n{'='*70}")
        print(f"MÉTRIQUES GLOBALES")
        print(f"{'='*70}")
        print(f"Véhicules utilisés      : {metrics['num_vehicles']}")
        print(f"Changements de produit  : {metrics['num_product_changes']}")
        print(f"Coût changements        : {metrics['total_changeover_cost']:.2f}")
        print(f"Distance totale         : {metrics['total_distance']:.2f} km")
        print(f"Coût total              : {metrics['total_cost']:.2f}")
        print(f"Temps de calcul         : {metrics['computation_time']:.3f} s")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    print("Module MPVRP-CC OR-Tools chargé avec succès !")
    print("Utilisez instance_manager.py pour créer et tester des instances.")
