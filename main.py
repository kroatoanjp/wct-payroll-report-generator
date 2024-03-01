from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, date
import json
import logging

from trello import TrelloClient

from activity_report import ActivityReport, ActivityTimeRange
import card_filter
from trello_board import TrelloBoard, TrelloBoardFactory, TrelloCredentials

logger = logging.getLogger(__name__)

@dataclass
class BaseConfig:
    time_range_mode: bool
    start_date: date
    end_date: date
    verbose: date
    cache_folder: str
    reports_folder: str

def parse_date(date_str):
    return date.fromisoformat(date_str)

def parse_args() -> BaseConfig:
    parser = ArgumentParser(
        description="Generates Trello activity reports",
        formatter_class=ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-s', '--start-date', help="YYYY-MM-DD report start date (inclusive)")
    parser.add_argument('-e', '--end-date', help="YYYY-MM-DD report end date (inclusive)")
    parser.add_argument('-r', '--reports-dir', 
                        default="reports/",
                        help="directory in which to output generated reports")
    parser.add_argument('-c', '--cache-dir', 
                        default="cache/",
                        help="directory in which to cache Trello table data")
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()

    if args.start_date and args.end_date:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
        if end_date < start_date:
            raise ValueError(
                "End date cannot come before start date. " + \
                f"start_date: {args.start_date}, end_date: {args.end_date}"
            )
        time_range_mode = True
    elif not (args.start_date or args.end_date):
        start_date = None
        end_date = None
        time_range_mode = False
    else:
        raise ValueError(
            "Expected values for both start_date and end_date. " + \
            f"start_date: {args.start_date}, end_date: {args.end_date}"
        )

    if not os.path.isdir(args.cache_dir):
        raise ValueError(
            f"Expected directory path for cache_dir: {args.cache_dir}"
        )
    if not os.path.isdir(args.reports_dir):
        raise ValueError(
            f"Expected directory path for reports_dir: {args.reports_dir}"
        )
    config = BaseConfig(
        time_range_mode = time_range_mode,
        start_date = start_date,
        end_date = end_date,
        verbose = args.verbose,
        cache_folder = args.cache_dir,
        reports_folder = args.reports_dir,
    )
    return config

def main():
    args = parse_args()
    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level)
    logger.debug(f"Running with config: {args}")

    credentials = TrelloCredentials.default_credentials()
    board_factory = TrelloBoardFactory(
        credentials=credentials, 
        cache_folder=args.cache_folder
    )
     
    if args.time_range_mode:
        activity_report = ActivityReport(
            board_factory=board_factory,
            time_range=ActivityTimeRange(
                start_date=args.start_date,
                end_date=args.end_date,
            ),
            reports_folder=args.reports_folder
        )
    else:
        activity_report = ActivityReport(
            board_factory=board_factory,
            reports_folder=args.reports_folder
        )  

    ALIGNMENT_BOARD_ID = "65771411615cf97225e48f04"
    MTL_BOARD_ID = "61d77b3c650da472e3516146"
    
    activity_report.record_board_activity(
        board_id=MTL_BOARD_ID, 
        done_column="Done", 
        card_tag=None,
        include_filters=[
            card_filter.NameStartsWith("Arc ")
        ]
    )

    activity_report.record_board_activity(
        board_id=MTL_BOARD_ID, 
        done_column="Done", 
        card_tag="[Non-WN]",
        exclude_filters=[
            card_filter.NameStartsWith("Arc "),
            card_filter.NameContains("Kasaneru"),
        ]
    )

    activity_report.record_board_activity(
        board_id=ALIGNMENT_BOARD_ID, 
        done_column="Finished", 
        card_tag='[Realignment]'
    )

    activity_report.save()

    logger.info(f"Unregistered Recipients: {activity_report.unregistered_recipients}")

if __name__ == "__main__": 
    main()