from library import DialogflowLibrary as dl

# flow = dl.get_flow("test_flow11")
# page = dl.get_page(flow, "source")
# print(page.name)
flow = dl.create_flow("test_flow18")

page_end = dl.create_page(flow, "end")
event_handler1 = dl.create_event_handler(
    name="a", event="sys.no-input-1", target_page=page_end
)
event_handler2 = dl.create_event_handler(
    name="a", event="sys.no-input-2", target_page=page_end
)
event_handler3 = dl.create_event_handler(
    name="a", event="sys.no-input-3", target_page=page_end
)
# webhook = dl.get_webhook("mywebhook")
# print(webhook.name)


# fullfillment_entry = dl.create_fulfillment(
#     messages=[dl.create_response_message("Entry Fullfilment")],
#     set_parameter_actions=[
#         dl.create_set_parameter_action("entry", "fullfill")
#     ],
#     webhook=webhook,
#     tag="w",
# )


page_source = dl.create_page(
    flow,
    "source",
    event_handlers=[event_handler1, event_handler2, event_handler3],
)
# page_end = dl.create_page(flow, "end")
# page_success = dl.create_page(
#     flow, "success", entry_fulfillment=fullfillment_entry
# )


# intent = dl.get_intent("Default Welcome Intent")
condition = "$session.params = null AND $session.params = null"
fullfillment = dl.create_fulfillment(
    messages=[dl.create_response_message("Hello world")],
    set_parameter_actions=[
        dl.create_set_parameter_action("test_param", "test_value")
    ],
    # webhook="mywebhook",
    # tag='w'
)

# fullfillment2 = dl.create_fulfillment(
#     messages=[dl.create_response_message("Hello world1")],
# )
transition1 = dl.create_transition_route(
    condition=condition,
    target_page=page_source,
    trigger_fulfillment=fullfillment,
)
# transition2 = dl.create_transition_route(
#     intent=intent,
#     target_page=page_end,
#     trigger_fulfillment=fullfillment2,
# )
# transition3 = dl.create_transition_route(intent=intent,
# target_page=page_success)


dl.add_transition_route(flow, transition1)
# dl.add_transition_route(page_source, transition2)
# dl.add_transition_route(page_end, transition3)
