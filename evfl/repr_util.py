import typing

from evfl.event import Event, ActionEvent, SwitchEvent, ForkEvent, JoinEvent, SubFlowEvent
from evfl.evfl import EventFlow
from evfl.util import make_values_to_index_map

class _GraphBuilder:
    def __init__(self) -> None:
        self.elements: list = []

    def add_node(self, node_id: int, node_type: str, data = dict()) -> int:
        self.elements.append({
            'type': 'node',
            'id': node_id,
            'data': data,
            'node_type': node_type,
        })
        return node_id

    def add_edge(self, source: int, target: int, data = dict()) -> None:
        self.elements.append({
            'type': 'edge',
            'source': source,
            'target': target,
            'data': data,
        })

def generate_flowchart_graph(flow: EventFlow) -> list:
    if not flow.flowchart:
        return list()

    actors = flow.flowchart.actors
    events = flow.flowchart.events
    builder = _GraphBuilder()
    visited: typing.Set[Event] = set()

    event_idx_map = make_values_to_index_map(events)

    def handle_next(nid, next_event: typing.Optional[Event], join_stack: typing.List[Event]) -> None:
        if not next_event:
            if join_stack:
                builder.add_edge(nid, event_idx_map[join_stack[-1]], {'virtual': True})
            return
        builder.add_edge(nid, event_idx_map[next_event])
        traverse(next_event, join_stack)

    def traverse(event: Event, join_stack: typing.List[Event]) -> None:
        if event in visited:
            return
        visited.add(event)
        data = event.data

        if isinstance(data, ActionEvent):
            nid = builder.add_node(event_idx_map[event], 'action', {
                'actor': str(data.actor.v.identifier),
                'action': str(data.actor_action.v),
                'name': event.name,
                'params': data.params.data if data.params else None,
            })
            handle_next(nid, data.nxt.v, join_stack)

        elif isinstance(data, SwitchEvent):
            nid = builder.add_node(event_idx_map[event], 'switch', {
                'actor': str(data.actor.v.identifier),
                'query': str(data.actor_query.v),
                'name': event.name,
                'params': data.params.data if data.params else None,
            })
            for value, case in data.cases.items():
                builder.add_edge(nid, event_idx_map[case.v], {'value': value})
                traverse(case.v, join_stack)
            if join_stack and not (len(data.cases) == 2 and 0 in data.cases and 1 in data.cases):
                builder.add_edge(nid, event_idx_map[join_stack[-1]], {'virtual': True})

        elif isinstance(data, ForkEvent):
            nid = builder.add_node(event_idx_map[event], 'fork', {'name': event.name})
            join_stack.append(data.join.v)
            for fork in data.forks:
                builder.add_edge(nid, event_idx_map[fork.v])
                traverse(fork.v, join_stack)
            traverse(data.join.v, join_stack)

        elif isinstance(data, JoinEvent):
            join_stack.pop()
            nid = builder.add_node(event_idx_map[event], 'join', {'name': event.name})
            handle_next(nid, data.nxt.v, join_stack)

        elif isinstance(data, SubFlowEvent):
            nid = builder.add_node(event_idx_map[event], 'sub_flow', {
                'res_flowchart_name': data.res_flowchart_name,
                'entry_point_name': data.entry_point_name,
                'name': event.name,
                'params': data.params.data if data.params else None,
            })
            handle_next(nid, data.nxt.v, join_stack)

    for i, entry in enumerate(flow.flowchart.entry_points):
        builder.add_node(-1000-i, 'entry', {'name': entry.name})
        builder.add_edge(-1000-i, event_idx_map[entry.main_event.v])
        traverse(entry.main_event.v, [])

    # Add events that are not linked from any entry point.
    # This may generate incomplete graphs.
    try:
        for event in flow.flowchart.events:
            if event in visited:
                continue
            traverse(event, [])
    except IndexError as e:
        pass

    return builder.elements
