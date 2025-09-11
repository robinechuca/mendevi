#!/usr/bin/env python3

"""CLI entry point to visualize database data."""

from context_verbose import Printer
import click

from .parse import parse_videos_database


@click.command()
@click.argument("database", type=click.Path())
def main(database: str):
    """Draw a chart from a database.

    \b
    Parameters
    ----------
    database : pathlike, optional
        The path to the database where all measurements are stored.
        If a folder is provided, the database is created inside this folder.
    """
    with Printer("Parse configuration...") as prt:
        _, database = parse_videos_database(prt, (), database)


    import plotly.express as px
    df = px.data.iris()
    df["e"] = df["sepal_width"]/100
    fig = px.scatter(df, x="sepal_width", y="sepal_length", color="species",
                     error_x="e", error_y="e")
    fig.show()

