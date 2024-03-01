from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
import json
import logging

import card_filter

logger = logging.getLogger(__name__)

@dataclass
class ActivityTimeRange:
    start_date: date
    end_date: date

    def get_period_key(self):
        zero_filled_start_month = str(self.start_date.month).zfill(2)
        zero_filled_start_day = str(self.start_date.day).zfill(2)
        start_year = self.start_date.year
        zero_filled_end_month = str(self.end_date.month).zfill(2)
        zero_filled_end_day = str(self.end_date.day).zfill(2)
        end_year = self.end_date.year
        card_month_key = f"{start_year}-{zero_filled_start_month}-{zero_filled_start_day}" + \
                         f"_to_{end_year}-{zero_filled_end_month}-{zero_filled_end_day}"
        return card_month_key

@dataclass
class MemberActivityRecord:
    card_count: int
    card_titles: list
    current_payroll: str
    discord: str = None
    card_percent: float = 0
    payroll_card_percent: float = 0

@dataclass
class ReportRecordInfo:
    unique_period_subparts: int = 0
    payroll_qualifying_subparts: int = 0

@dataclass
class ReportRecord:
    info: ReportRecordInfo
    members: dict[str, MemberActivityRecord]

    def to_dict(self):
        report_dict = {}
        report_dict["_info"] = asdict(self.info)
        sorted_member_records = sorted(
            self.members.items(), 
            key=lambda x:x[1].card_count, 
            reverse=True
        )
        for member, member_data in sorted_member_records:
            report_dict[member] = asdict(member_data)
        return report_dict

    @staticmethod
    def empty_record():
        record_info = ReportRecordInfo()
        members = {}
        return ReportRecord(
            info = record_info,
            members = members
        )


class ActivityReport:
    def __init__(self, board_factory, time_range=None, reports_folder="reports"):
        self.unregistered_recipients = set()
        self.data = {}
        self._recipient_file_name = "patreon_recipients.json"
        self._recipient_data = self._get_patreon_recipients()
        self._board_factory = board_factory
        self._time_range = time_range
        self._reports_folder = reports_folder



    def _get_patreon_recipients(self):
        logger.info(f"Reading patreon recipient data from file: {self._recipient_file_name}")
        with open(self._recipient_file_name) as infile:
            recipient_data = json.loads(infile.read())
        logger.debug(f"Read patreon recipient data from file: {self._recipient_file_name}")
        return recipient_data

    def save(self):
        logger.info("Saving activity report")
        for card_month_key, report in self.data.items():
            report_file = f"{self._reports_folder}/trello-activity-{card_month_key}.json"
            logger.debug(f"Writing report for month: {card_month_key} to file: {report_file}")
            with open(report_file, "w") as outfile:
                report_dict = report.to_dict()
                outfile.write(json.dumps(report_dict, indent=4, ensure_ascii=False))
            logger.debug(f"Wrote report for month: {card_month_key} to file: {report_file}")
        logger.debug("Saved activity report")
    
    def _get_subpart_count(self, description):
        desc_lines = description.split("\n")
        subpart_line = [line for line in desc_lines if "Est. Subparts:" in line]
        if len(subpart_line) == 0:
            return 1
        subpart_line = subpart_line[0]
        subpart_count = subpart_line.split("Est. Subparts:")[1].strip()
        return int(subpart_count)


    def _get_movement_to_column(self, card, column_name):
        movements = [x for x in card.props.card_movements if column_name in x['destination']['name']]
        if len(movements) == 0:
            return None
        return movements[0]

    def _group_cards_by_month(self, board, done_column):
        month_grouped_cards = defaultdict(list)
        for card in board.cards:
            # In order to consistently process long-running cards (ie. cards
            # that are worked on across more than one month), all cards will
            # be separated by the date on which they are finished.
            card_finish_movement = self._get_movement_to_column(card, done_column)
            if not card_finish_movement:
                continue
            # If a time range has been specified, a single report will be
            # generated with all cards that fall in that time range (only
            # one card_month_key for the entire range).
            # Otherwise, a report will be generated for each month of data
            # (each month will have its own card_month_key).
            card_finish_date = card_finish_movement['datetime'].date()
            if self._time_range:
                if card_finish_date < self._time_range.start_date or \
                    card_finish_date > self._time_range.end_date:
                    continue
                card_month_key = self._time_range.get_period_key()
            else:
                zero_filled_month = str(card_finish_date.month).zfill(2)
                card_month_key = f"{card_finish_date.year}-{zero_filled_month}"

            card.props.subpart_count = self._get_subpart_count(card.description)
            card.props.members = set()
            card.props.payroll_members = set()
            for member_id in card.idMembers:
                member = board.get_member_by_id(member_id) 
                card.props.members.add(member)
                if member in self._recipient_data:
                    if self._recipient_data[member]['current_payroll'] == "yes":
                        card.props.payroll_members.add(member)
                else:
                    # Keep a record of any card members that have not 
                    # been added to the payroll data sheet
                    self.unregistered_recipients.add(member)
            month_grouped_cards[card_month_key].append(card)
        return month_grouped_cards

    def _filter_cards(self, cards, include_filters, exclude_filters):
        filtered_cards = []
        for card in cards:
            # If include filters are specified, a card must match all
            # include filters to not be filtered out
            if include_filters:
                if not all([card_filter.matches(card) for card_filter in include_filters]):
                    continue
            # If exclude filters are specified, a card that matches any
            # exclude filters will be filtered out
            if exclude_filters:
                if any([card_filter.matches(card) for card_filter in exclude_filters]):
                    continue
            filtered_cards.append(card)
        return filtered_cards

    def _update_summary_stats(self, report, filtered_cards):
        for card in filtered_cards:
            subpart_count = card.props.subpart_count
            payroll_subpart_count = len(card.props.payroll_members) * subpart_count
            report.info.unique_period_subparts += subpart_count
            report.info.payroll_qualifying_subparts += payroll_subpart_count

    def _update_member_card_percentages(self, report):
        for member_data in report.members.values():
            member_data.card_percent = round(
                100 * member_data.card_count / report.info.unique_period_subparts, 
                2
            )
            if member_data.current_payroll == "yes":
                member_data.payroll_card_percent = round(
                    100 * member_data.card_count / report.info.payroll_qualifying_subparts, 
                    2
                )

    def _assign_card_to_member(self, report, member, card, card_tag):
        member_data = self._get_report_member_data(report, member)
        card_title = self._format_card_title(card, card_tag)
        member_data.card_count += card.props.subpart_count
        member_data.card_titles.append(card_title)
        member_data.card_titles.sort()


    def _format_card_title(self, card, card_tag):
        card_title = card.name
        if card.props.subpart_count > 1:
            card_title += f" (~{card.props.subpart_count} subparts)"
        if card_tag:
            card_title += f" {card_tag}"
        return card_title

    def _get_report_member_data(self, report:ReportRecord, member:str) -> MemberActivityRecord:
        if not member in report.members: 
            current_payroll = "unknown"
            discord = None
            if member in self._recipient_data:
                current_payroll = self._recipient_data[member]['current_payroll']
                discord = self._recipient_data[member]['discord']
            member_data = MemberActivityRecord(
                card_count = 0,
                card_titles = [],
                current_payroll = current_payroll,
                discord = discord
            )
            report.members[member] = member_data
        return report.members[member]


    def _get_data_by_key(self, card_month_key):
        if card_month_key not in self.data:
            new_record = ReportRecord.empty_record()
            self._set_data_by_key(card_month_key, new_record)
        report = self.data[card_month_key]
        return report

    def _set_data_by_key(self, card_month_key, report):
        self.data[card_month_key] = report

    def record_board_activity(self, 
            board_id, 
            done_column, 
            card_tag=None,
            include_filters=None,
            exclude_filters=None
        ):
        logger.info(f"Recording activity for board: {board_id}")
        board = self._board_factory.build(board_id)
        board.sync()
        month_grouped_cards = self._group_cards_by_month(board, done_column)
        for card_month_key, cards in month_grouped_cards.items():
            # If this card_month_key was used in a previous run of 
            # record_board_activity, the data for the current run should
            # be appended to that report. Otherwise, get_data_by_key will
            # return an empty record for a new report.
            report = self._get_data_by_key(card_month_key)
            filtered_cards = self._filter_cards(cards, include_filters, exclude_filters)
            self._update_summary_stats(report, filtered_cards)
            for card in filtered_cards:
                for member in card.props.members:
                    self._assign_card_to_member(
                        report=report, 
                        member=member, 
                        card=card, 
                        card_tag=card_tag
                    )
            self._update_member_card_percentages(report)
        logger.debug(f"Recorded activity for board: {board_id}")
