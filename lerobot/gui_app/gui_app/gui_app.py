"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config

# project imports
from .state import State


# @rx.page(on_load=State.on_cont_mount)
def index() -> rx.Component:
    # Welcome Page (Index)
    return rx.container(
        rx.vstack(
            rx.image(src=State.image),
            rx.text(State.image_text),
            rx.button("Teleoperate", on_click=State.teleop),
        ),
        
        # on_unmount=State.on_cont_unmount,
    )

app = rx.App()
app.add_page(index)
