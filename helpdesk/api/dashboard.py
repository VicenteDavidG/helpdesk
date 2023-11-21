from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Date
from frappe.query_builder.terms import Criterion
from frappe.utils.caching import redis_cache

from helpdesk.utils import get_customer, is_agent


@frappe.whitelist()
def get():
	if is_agent():
		return for_agent()
	return [by_date(), by_status()]


def base_query(table, date_start=None, date_end=None):
	user = frappe.session.user
	or_criterion = [table.contact == user, table.raised_by == user]
	and_criterion = []
	if date_start:
		and_criterion.append(table.creation >= date_start)
	if date_end:
		and_criterion.append(table.creation <= date_end)
	for c in get_customer(user):
		or_criterion.append(table.customer == c)
	return (
		frappe.qb.from_(table)
		.where(Criterion.any(or_criterion))
		.where(Criterion.all(and_criterion))
	)


def by_date():
	Ticket = frappe.qb.DocType("HD Ticket")
	return {
		"title": _("Tickets"),
		"is_chart": True,
		"chart_type": "Line",
		"data": (
			base_query(Ticket)
			.select(Date(Ticket.creation, "name"))
			.select(Count(Ticket.name, "value"))
			.groupby(Date(Ticket.creation))
			.run(as_dict=True)
		),
	}


def by_status():
	Ticket = frappe.qb.DocType("HD Ticket")
	return {
		"title": _("Status"),
		"is_chart": True,
		"chart_type": "Pie",
		"data": (
			base_query(Ticket)
			.select(Ticket.status.as_("name"))
			.select(Count(Ticket.name, "value"))
			.groupby(Ticket.status)
			.run(as_dict=True)
		),
	}


def for_agent():
	return [
		avg_first_response_time(),
		resolution_within_sla(),
		my_tickets(),
		ticket_statuses(),
		new_tickets(),
		ticket_types(),
		ticket_activity(),
		ticket_priority(),
	]


@redis_cache(ttl=60 * 5)
def ticket_statuses():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")]}

	res = frappe.db.get_list(
		"HD Ticket",
		fields=["count(name) as value", "status as name"],
		filters=filters,
		group_by="status",
	)

	return {
		"title": "Status",
		"is_chart": True,
		"chart_type": "Pie",
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def avg_first_response_time():
	average_resolution_time = float(0.0)
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {
		"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")],
		"resolution_time": ["not like", ""],
	}

	ticket_list = frappe.get_list(
		"HD Ticket",
		fields=["name", "resolution_time"],
		filters=filters,
	)

	for ticket in ticket_list:
		average_resolution_time += ticket.resolution_time

	res = "Not enough data"

	if ticket_list:
		h = round((((average_resolution_time) / len(ticket_list)) / 3600), 1)
		res = f"{h} Hours"

	return {
		"title": "Avg. first response time",
		"is_chart": False,
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def ticket_types():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")]}

	res = frappe.db.get_list(
		"HD Ticket",
		fields=["count(name) as value", "ticket_type as name"],
		filters=filters,
		group_by="ticket_type",
	)

	return {
		"title": "Type",
		"is_chart": True,
		"chart_type": "Pie",
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def new_tickets():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")]}

	res = frappe.db.get_list(
		"HD Ticket",
		fields=["COUNT(name) as value", "DATE(creation) as name"],
		filters=filters,
		group_by="DATE(creation)",
		order_by="DATE(creation)",
	)

	return {
		"title": "New tickets",
		"is_chart": True,
		"chart_type": "Line",
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def resolution_within_sla():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {
		"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")],
		"status": "Closed",
	}

	ticket_list = frappe.get_list(
		"HD Ticket",
		filters=filters,
		fields=["name", "agreement_status", "sla"],
	)

	count = 0

	for ticket in ticket_list:
		if ticket.agreement_status == "Fulfilled":
			count = count + 1

	res = "0%"

	if count:
		resolution_within_sla_percentage = (count / len(ticket_list)) * 100
		resolution_within_sla_percentage = round(resolution_within_sla_percentage, 1)

		res = str(resolution_within_sla_percentage) + "%"

	return {
		"title": "Resolution within SLA",
		"is_chart": False,
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def ticket_activity():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")]}

	res = frappe.db.get_list(
		"HD Ticket Activity",
		fields=["COUNT(name) as value", "DATE(creation) as name"],
		filters=filters,
		group_by="DATE(creation)",
		order_by="DATE(creation)",
	)

	return {
		"title": "Activity",
		"is_chart": True,
		"chart_type": "Line",
		"data": res,
	}


@redis_cache(ttl=60 * 5)
def ticket_priority():
	thirty_days_ago = datetime.now() - timedelta(days=30)
	filters = {"creation": [">=", thirty_days_ago.strftime("%Y-%m-%d")]}

	res = frappe.db.get_list(
		"HD Ticket",
		fields=["count(name) as value", "priority as name"],
		filters=filters,
		group_by="priority",
	)

	return {
		"title": "Priority",
		"is_chart": True,
		"chart_type": "Pie",
		"data": res,
	}


@redis_cache(ttl=60 * 5, user=True)
def my_tickets():
	QBTicket = frappe.qb.DocType("HD Ticket")
	like_str = f"%{frappe.session.user}%"
	like_query = QBTicket._assign.like(like_str)

	res = (
		frappe.qb.from_(QBTicket)
		.select(Count(QBTicket.name, "count"))
		.select(QBTicket.status)
		.where(like_query)
		.where(QBTicket.status.isin(["Open", "Replied"]))
		.groupby(QBTicket.status)
		.run(as_dict=True)
	)

	def map_row(row):
		return f"{row['count']} {row['status']}"

	res = " / ".join(map(map_row, res)).lower()

	return {
		"title": "My tickets",
		"is_chart": False,
		"data": res,
	}
