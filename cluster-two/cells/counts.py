"""Source-pinned numeric counter views and exact observer-count subtraction.

Schema: core/docs/architecture/70-daemon-application-startup-control.md.
Array order: application/diagnostics/schema.rs and resources.rs. This module
accepts explicit original endpoints; it never invents phase pairs from Debug,
wall time or neighboring calls. SDK spans remain instrumented complete spans.
"""
import argparse
import json
from pathlib import Path

SCHEMA_SOURCE = "core/docs/architecture/70-daemon-application-startup-control.md"
STATEMENT = ("attempts", "executions", "rows_returned", "rows_changed", "direct_rows_changed",
             "returned_blob_bytes", "returned_value_bytes", "vm_steps", "fullscan_steps", "sorts",
             "autoindex_rows", "reprepares", "bound_bytes", "sql_bytes", "statement_memory_samples",
             "statement_memory_sample_bytes", "elapsed_ns")
PAYLOAD = ("write_input_bytes", "write_cells", "partial_write_cells", "cell_copy_bytes", "cell_zeroed_bytes",
           "read_window_zeroed_bytes", "read_local_copy_bytes")
ALLOCATION = ("attempts", "requested_bytes", "admitted_jobs", "refusals", "observations", "freelist_queries")
OWNER_SCALARS = ("admitted", "credited_bytes", "peak_credited_bytes", "outstanding", "scheduler_bytes",
                 "queued", "peak_queued", "receipt_overruns", "receipt_overrun_bytes", "maintenance_jobs",
                 "maintenance_rows", "closed_namespaces", "maintenance_data_bytes", "maintenance_ns")
DIRECT_OWNER_SCALARS = ("jobs", "maintenance_jobs", "maintenance_rows", "closed_namespaces", "maintenance_data_bytes", "maintenance_ns")
DIRECT_MOUNT = ("active", "retained", "requests", "completed", "terminal")
DIRECT_DISPOSITION = ("served", "inline", "refused", "terminal", "forget_units", "store_units")
CLASSES = ("Read", "Mutation", "Capture", "Lifecycle", "OperationRecord", "Source")
STORED = ("wait_refs", "namespaces", "inode_rows", "directory_entry_rows", "payload_cells", "payload_bytes",
          "shrink_rows", "operation_record_rows", "operation_record_bytes", "orphan_rows", "owner_rows",
          "source_rows", "owner_details", "reply_tickets", "retire_targets", "maintenance_targets", "ready_targets")
# Original arrays remain readable for retained receipts. Step A reports memory
# separately and removes three SQL counters; it supplies section 32 as the
# explicit discriminator. No deleted counter is synthesized for current calls.
STORED_OPEN_MEMORY = tuple(name for name in STORED if name not in
                          {"wait_refs", "orphan_rows", "retire_targets"})
OPEN_STATE = ("kernel_entries", "directory_parents", "file_handles", "file_reads",
              "lookup_owners", "file_custody", "orphan_files", "generation_waits",
              "mounts", "directory_handles", "cookie_pages")
ALLOCATION_STATE = ("logical_bytes", "allocated_bytes", "high_water_allocated_bytes", "reserved_tail_bytes", "cleanup_headroom_bytes")
STORAGE = ("policy", "locate", "read_packs", "read_pack_selections", "whole_selected", "whole_due_density",
           "whole_due_singleton", "whole_due_small", "whole_due_reuse", "range_selected", "range_scan_bytes",
           "range_acquired_bytes", "range_materialized_bytes", "value_groups", "signatures", "reserve",
           "initial_reservations", "reservation_refills", "publish", "payload_reads", "payload_read_bytes",
           "pack_read_bytes", "pack_write_bytes", "pooled_packs", "pooled_groups", "reserved_directory_bytes",
           "ordinal_reservations", "locator_hits", "locator_misses", "locator_evictions", "locator_eviction_probes",
           "locator_second_chances", "locator_bookkeeping_live_peak_bytes", "pack_hits", "pack_misses",
           "pack_evictions", "pack_evicted_bytes", "directory_validations", "directory_unshared_walks",
           "directory_entry_bounds", "prefetch_group_decodes", "forced_seals")
STORE = ("object_batches", "object_ids", "length_batches", "length_ids", "serial_reservations")
READER = ("stopping", "poisoned", "readers", "quarantined", "waiting", "assigned", "leased", "outstanding",
          "peak_outstanding", "grants", "queue_wait_ns", "maximum_queue_wait_ns", "scheduler_bytes")
CACHE = ("cache_hits", "cache_misses", "upstream_batches", "authenticated_bytes", "evictions", "charged_cache_bytes", "cached_objects",
         "seeded_objects", "seeded_bytes", "seeded_lengths")
# The five leading counters and the three seeded counters only grow; the two between them are gauges.
CACHE_COUNTERS = CACHE[:5] + CACHE[7:]
CONSTRUCTION = ("inode_rows", "entry_rows", "inode_pages", "entry_pages", "change_pages", "largest_page",
                "parent_points", "base_lookups", "headers_written", "headers_dropped", "values_written",
                "fresh_serials", "tombstones_skipped", "files_constructed", "files_unchanged", "symlinks",
                "metadata_built", "metadata_patched", "record_jobs", "header_opens", "header_rows", "header_points",
                "change_opens", "change_rows", "change_points", "value_opens", "value_rows", "value_points",
                "fresh_opens", "fresh_rows", "fresh_points")
GLOBAL_SQL = ("statements", "vm_steps", "fullscan_steps", "sorts", "autoindex_rows", "reprepares", "returned_rows",
              "bound_bytes", "statement_ns", "commit_ns", "transactions", "write_transactions", "write_commits",
              "commits", "read_snapshots", "rollbacks", "transaction_ns", "read_snapshot_ns", "sealed_inserts",
              "sealed_body_bytes", "blob_open_calls", "blob_reopen_calls", "blob_read_calls", "blob_requested_bytes",
              "blob_read_bytes", "blob_read_ns", "blob_close_calls")
DISPATCH = ("configured_workers", "entered_workers", "live_workers", "mounts", "queued", "running", "parked", "retained", "stopping", "failed")
NATIVE = ("owner_id", "root_serial", "serving", "detached", "abort_bound")
LOOPS = ("phase", "revision", "configured", "created", "entered", "exited", "joined")
MOUNT = ("received", "admitted", "queued", "running", "parked", "retained", "owned_input_bytes", "future_bytes",
         "receive_units", "completed", "steps", "wakes", "terminal")
OPCODE_DISPOSITION = ("handoffs", "inline", "refused", "terminal", "unadmitted", "forget_units", "store_units")
OPERATIONS = {"mount": (1,9), "commit": (2,), "workspace_status": (3,), "unmount": (4,), "cleanup": (13,)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity(group):
    header = group[0]
    return (tuple(header["daemon"]), tuple(header["scope"]), header["call"])


def names(values, keys):
    require(len(values) == len(keys), "source counter schema cardinality mismatch")
    require(all(type(value) is int and 0 <= value < 2**64 for value in values), "source counter values must be u64")
    return dict(zip(keys, values))


def row(group, section, index=0):
    found = [item for item in group if item["section"] == section and item["index"] == index]
    require(len(found) <= 1, "duplicate original counter row")
    if not found or not found[0]["available"]:
        return None
    return found[0]["values"]


def decode(group):
    result = {"identity": identity(group), "operation_tag": group[0]["values"][0],
              "namespace": group[0]["index"], "schema_source": SCHEMA_SOURCE,
              "field_availability": {}}
    direct = row(group, 33)
    direct_mode = direct is not None
    if direct_mode:
        require(len(direct) == 1 and direct[0] in {0,1}, "direct Workspace marker cardinality/bit")
        result["service_schema"] = "issue321-direct-workspace"
        result["sqlite_cache_group"] = {"memory_management_enabled": bool(direct[0])}
    class_marker = row(group, 37)
    require(class_marker is None or (direct_mode and class_marker == [3]), "frontier class marker")
    classes = ("General", "Mutation", "Source") if class_marker is not None else CLASSES
    class_count = len(classes)
    scalar = row(group, 1)
    budget = row(group, 31)
    holds = row(group, 35)
    if holds is not None:
        require(direct_mode and len(holds) == 3, "lock-only hold schema cardinality")
        result["lock_only_holds"] = names(holds, ("observations", "reply_attempts", "reply_hold_ns"))
    if direct_mode:
        require(budget is None, "direct Workspace emitted retired budget")
    if budget is not None:
        result["overlay_budget"] = names(budget, ("limit_bytes", "pager_allowance_bytes", "fixed_bytes",
            "job_bytes", "peak_job_bytes", "outstanding", "memory_management_enabled"))
    if not direct_mode:
        result["field_availability"]["overlay_budget"] = "AVAILABLE" if budget is not None else "UNAVAILABLE"
    if scalar is not None:
        require(len(scalar) == (6 + 3 * class_count if direct_mode else 32), "owner scalar/class schema cardinality")
        fields = DIRECT_OWNER_SCALARS if direct_mode else OWNER_SCALARS
        result["owner"] = names(scalar[:len(fields)], fields)
        slices = (("jobs_by_class",6),("lock_wait_ns",6+class_count),("hold_ns",6+2*class_count)) if direct_mode else (("completed",14),("queue_wait_ns",20),("service_ns",26))
        for key, offset in slices:
            result["owner"][key] = names(scalar[offset:offset+class_count], classes)
    reader_marker = row(group, 39)
    require(reader_marker is None or reader_marker == [1], "Workspace reader schema marker")
    reader_fields = ("stopping", "poisoned", "readers", "quarantined", "opening_failures", "requests", "lock_wait_ns") if reader_marker is not None else READER
    for key, section, fields in (("store",8,STORE), ("reader",9,reader_fields), ("cache",10,CACHE),
                                 ("construction",15,CONSTRUCTION), ("storage",16,STORAGE), ("dispatch",11,DISPATCH),
                                 ("native",12,NATIVE), ("loops",24,LOOPS), ("mount",25,MOUNT),
                                 ("payload_foreground",4,PAYLOAD), ("payload_maintenance",5,PAYLOAD),
                                 ("allocation_foreground",6,ALLOCATION), ("allocation_maintenance",7,ALLOCATION)):
        values = row(group, section)
        if direct_mode and key == "dispatch":
            require(values is None, "direct Workspace emitted retired dispatcher")
            continue
        if direct_mode and key == "mount": fields = DIRECT_MOUNT
        if values is not None:
            result[key] = names(values, fields)
        result["field_availability"][key] = "AVAILABLE" if values is not None else "UNAVAILABLE"
    family_marker = row(group, 36)
    require(family_marker is None or family_marker in ([12], [14]), "statement family cardinality marker")
    family_count = family_marker[0] if family_marker is not None else 14
    for key, section in (("sql_foreground",2), ("sql_maintenance",3)):
        families = [row(group, section, index) for index in range(family_count)]
        if all(values is not None for values in families):
            result[key] = [names(values, STATEMENT) for values in families]
        result["field_availability"][key] = "AVAILABLE" if key in result else "UNAVAILABLE"
    resource_marker = row(group, 38)
    require(resource_marker is None or resource_marker == [1], "Workspace resource scope marker")
    result["resource_scope"] = "workspace" if resource_marker is not None else "daemon"
    values, open_values = row(group, 28), row(group, 32)
    result["field_availability"]["open_state"] = "AVAILABLE" if open_values is not None else "UNAVAILABLE"
    if open_values is not None:
        require(values is not None, "memory ownership without resource observation")
        result["open_state"] = names(open_values, OPEN_STATE)
    if values is not None:
        fields = STORED_OPEN_MEMORY if open_values is not None else STORED
        require(len(values) == len(fields) + 14, "resource schema cardinality")
        at = len(fields)
        result["resource_schema"] = ("issue321-open-memory" if open_values is not None else "original-sql-ownership")
        result["stored_counts"] = names(values[:at], fields)
        result["allocation_state"] = names(values[at:at+5], ALLOCATION_STATE)
        result["allocation_work"] = names(values[at+5:at+11], ALLOCATION)
        result["pages"] = names(values[at+11:], ("database_pages", "free_pages", "debt_upper_bytes"))
    result["reader_storage"] = {item["index"]: names(item["values"], STORAGE) for item in group
                                if item["section"] == 29 and item["available"]}
    opcode = row(group,26)
    if opcode is not None:
        require(len(opcode) == (45 if direct_mode else 46), "opcode/disposition source schema cardinality")
        result["opcodes"] = {"by_opcode": opcode[:39], "disposition": names(opcode[39:], DIRECT_DISPOSITION if direct_mode else OPCODE_DISPOSITION)}
    for section, field in ((13,"global_sql_writer"),(14,"global_sql_readers")):
        selected = {}
        for item in group:
            if item["section"] != section or not item["available"]:
                continue
            values = item["values"]
            require(len(values) == 55, "global SQL scalar/phase source schema cardinality")
            work = names(values[:27],GLOBAL_SQL)
            work["statement_phases"] = [names(values[27+2*index:29+2*index],("calls","wall_ns")) for index in range(7)]
            work["commit_phases"] = [names(values[41+2*index:43+2*index],("calls","wall_ns")) for index in range(7)]
            selected[item["index"]] = work
        if selected:
            result[field] = selected
    cost = row(group, 30)
    if cost is not None:
        full = 34 if direct_mode else 35
        require(len(cost) in {2,full} and cost[0] in {0,1} and cost[1] in {0,1}, "observer cost schema cardinality/bits")
        result["observer"] = {("attempted" if direct_mode else "admitted"): bool(cost[0]), "completion_available": bool(cost[1])}
        if cost[1]:
            require(len(cost) == full and cost[0] == 1, "completed observer work requires original attempt")
            result["observer"].update(sql=names(cost[2:19], STATEMENT), payload=names(cost[19:26], PAYLOAD),
                                      allocation=names(cost[26:32], ALLOCATION),
                                      times=names(cost[32:], ("lock_wait_ns", "hold_ns") if direct_mode else ("parked_turns", "queue_wait_ns", "service_ns")))
            if direct_mode:
                jobs = row(group, 34)
                require(jobs is not None, "direct observer job count missing")
                result["observer"].update(names(jobs, ("jobs",)))
        else:
            require(len(cost) == 2 and (not direct_mode or row(group,34) is None), "unavailable observer work must not fabricate counter arrays")
    return result


def correlate(events, groups):
    """Exact successful control record ranges; failure ranges stay unavailable."""
    origins = [event for event in events if event.get("event") == "control_origin"]
    require(len(origins) == 1 and origins[0].get("fields", {}).get("control_send_records") == 1,
            "fresh serve Control origin must establish exactly one Hello")
    decoded = {identity(group): decode(group) for group in groups.values()}
    require(len(decoded) == len(groups), "duplicate original daemon/scope/call identity")
    mapped = set()
    correlation = []
    previous = 1
    for event in events:
        codes = OPERATIONS.get(event.get("event"))
        if codes is None:
            continue
        fields = event.get("fields", {})
        before, after = fields.get("control_send_records_before"), fields.get("control_send_records_after")
        require(type(before) is int and type(after) is int and before == previous and after-before == len(codes),
                "successful facade control range differs from original completed send records")
        selected = []
        for call, code in zip(range(before+1,after+1), codes):
            matches = [(key,value) for key,value in decoded.items() if key[2] == call]
            require(len(matches) == 1, "original numeric group missing or cross-scope call ambiguity")
            key, value = matches[0]
            require(value["operation_tag"] == code and key not in mapped, "original call operation mismatch or duplicate mapping")
            mapped.add(key)
            selected.append(key)
        correlation.append({"event_sequence": event["sequence"], "event": event["event"],
                            "before_records": before, "after_records": after, "identities": selected,
                            "span_scope": "instrumented complete SDK; observer acquisition/format/transport included"})
        if event["event"] == "workspace_status":
            available = fields.get("status_state_attribution_available")
            jobs = fields.get("status_state_lifecycle_jobs")
            require(available is None or type(available) is int and available in {0,1}, "typed Status State attribution bit invalid")
            if available == 1:
                require(type(jobs) is int and jobs == 1, "typed original Status local Some requires exactly one State Lifecycle job")
                correlation[-1]["status_state"] = {"status": "AVAILABLE", "Lifecycle_jobs": jobs,
                            "provenance": "original typed Status.local Some; actual State SQL VM work unavailable"}
            else:
                require(jobs is None, "unavailable typed Status state must not fabricate job count")
                correlation[-1]["status_state"] = {"status": "UNAVAILABLE", "reason": "original local outcome missing or unavailable; no retrospective inference"}
        previous = after
    require(mapped == set(decoded), "unmapped numeric groups; never infer successful failure calls")
    return correlation


def difference(before, end, keys):
    result = {}
    for key in keys:
        left, right = before[key], end[key]
        require(left != 2**64-1 and right != 2**64-1 and right >= left, "cumulative counter decreased or saturated: " + key)
        result[key] = right-left
    return result


def resolve_selectors(selectors, bindings, correlation):
    """Resolve prospective logical endpoints against original successful ranges."""
    by_sequence = {item["event_sequence"]:item for item in correlation}
    require(len(by_sequence) == len(correlation), "duplicate original correlated event sequence")
    result = []
    for selected in selectors:
        resolved = {"label":selected["label"],"selectors":selected,"status":"UNAVAILABLE"}
        try:
            for role in ("before","end"):
                binding = bindings[selected[role]]
                original = by_sequence[binding["event_sequence"]]
                require(original["event"] == binding["event"], "original endpoint event type mismatch")
                position = binding["position"]
                require(position in {"first","last"}, "endpoint position must select first/last original successful call")
                identities = original["identities"]
                require(identities, "original endpoint has no successful numeric group")
                resolved[role+"_identity"] = identities[0 if position == "first" else -1]
                resolved[role+"_original"] = binding
            resolved["status"] = "RESOLVED"
        except (KeyError,ValueError,TypeError,IndexError) as error:
            resolved["reason"] = str(error)
        result.append(resolved)
    return result


def phase_counts(groups, before_identity, end_identity, *, exclusive_observer_scope=False, label="explicit interval", control_correlation=None):
    """Count-only subtraction over caller-selected original snapshot endpoints."""
    result = {"schema": "r7-phase-counts-v1", "status": "UNAVAILABLE", "label": label,
              "before_identity": before_identity, "end_identity": end_identity,
              "attribution_scope": "daemon-shared; concurrency not attributed to one Workspace",
              "time_scope": "instrumented; no formatter/transport/wait/service time subtraction",
              "gauges_and_peaks": "absolute original snapshots; never subtracted",
              "observer_credit": "caller Completion drop does not prove publisher Arc/credit already released"}
    try:
        require(exclusive_observer_scope, "observer channel exclusivity unavailable; other observers may affect cumulative counts")
        before_identity = (tuple(before_identity[0]), tuple(before_identity[1]), before_identity[2])
        end_identity = (tuple(end_identity[0]), tuple(end_identity[1]), end_identity[2])
        require(before_identity[:2] == end_identity[:2] and before_identity[2] < end_identity[2], "endpoint daemon/scope/order mismatch")
        snapshots = {identity(group): decode(group) for group in groups.values()}
        require(len(snapshots) == len(groups), "duplicate original snapshot identity")
        before, end = snapshots[before_identity], snapshots[end_identity]
        result["original_snapshots"] = {"before": before, "end": end}
        require("owner" in before and "owner" in end and "sql_foreground" in before and "sql_foreground" in end,
                "original endpoint owner/SQL snapshot unavailable")
        interval = [value for key,value in snapshots.items() if key[:2] == before_identity[:2] and before_identity[2] < key[2] <= end_identity[2]]
        require(len(interval) == end_identity[2]-before_identity[2], "original interval observer call missing")
        require(all(value.get("observer", {}).get("completion_available") or
                    (value.get("resource_scope") == "workspace" and value.get("observer", {}).get("attempted") is False)
                    for value in interval), "exact observer work unavailable in interval")
        observed = [value for value in interval if value.get("observer", {}).get("completion_available")]
        statement_keys = tuple(key for key in STATEMENT if key != "elapsed_ns")
        direct_mode = before.get("service_schema") == "issue321-direct-workspace"
        require(direct_mode == (end.get("service_schema") == "issue321-direct-workspace"), "mixed service schemas in one interval")
        owner_count = "jobs" if direct_mode else "admitted"
        class_count = "jobs_by_class" if direct_mode else "completed"
        owner_keys = ("jobs", "maintenance_jobs", "maintenance_rows", "closed_namespaces", "maintenance_data_bytes") if direct_mode else ("admitted", "receipt_overruns", "receipt_overrun_bytes", "maintenance_jobs", "maintenance_rows", "closed_namespaces", "maintenance_data_bytes")
        raw_owner = difference(before["owner"], end["owner"], owner_keys)
        classes = tuple(before["owner"][class_count])
        require(classes == tuple(end["owner"][class_count]), "mixed frontier class schemas in one interval")
        raw_classes = difference(before["owner"][class_count], end["owner"][class_count], classes)
        observer_class = "General" if "General" in classes else "Read"
        raw_sql = [difference(left,right,statement_keys) for left,right in zip(before["sql_foreground"],end["sql_foreground"])]
        observer_sql = {key: sum(value["observer"]["sql"][key] for value in observed) for key in statement_keys}
        observer_jobs = sum(value["observer"]["jobs"] for value in observed) if direct_mode else len(observed)
        require(raw_owner[owner_count] >= observer_jobs and raw_classes[observer_class] >= observer_jobs, "observer jobs exceed original cumulative delta")
        adjusted_owner, adjusted_classes = dict(raw_owner), dict(raw_classes)
        adjusted_owner[owner_count] -= observer_jobs
        adjusted_classes[observer_class] -= observer_jobs
        adjusted_sql = [dict(values) for values in raw_sql]
        for key in statement_keys:
            require(adjusted_sql[0][key] >= observer_sql[key], "observer Startup work exceeds original family delta: " + key)
            adjusted_sql[0][key] -= observer_sql[key]
        result.update(status="AVAILABLE", raw={"owner": raw_owner, class_count: raw_classes, "sql_foreground": raw_sql},
                      observer={"jobs": observer_jobs, "Read_completions": observer_jobs, "Startup_statement_work": observer_sql,
                                "original_costs": [value["observer"] for value in observed],
                                "explicit_no_attempt": [value["identity"] for value in interval if value not in observed]},
                      adjusted={"owner": adjusted_owner, class_count: adjusted_classes, "sql_foreground": adjusted_sql})
        status_calls = {value["identity"] for value in interval if value["operation_tag"] == 3}
        states = {tuple((tuple(key[0]),tuple(key[1]),key[2])): item.get("status_state", {})
                  for item in (control_correlation or []) if item["event"] == "workspace_status" for key in item["identities"]}
        if all(states.get(key, {}).get("status") == "AVAILABLE" for key in status_calls):
            jobs = sum(states[key]["Lifecycle_jobs"] for key in status_calls)
            state_class = "General" if "General" in classes else "Lifecycle"
            require(adjusted_owner[owner_count] >= jobs and adjusted_classes[state_class] >= jobs,
                    "typed Status State jobs exceed original post-Resources cumulative delta")
            without_status_owner, without_status_classes = dict(adjusted_owner), dict(adjusted_classes)
            without_status_owner[owner_count] -= jobs
            without_status_classes[state_class] -= jobs
            result["status_state_attribution"] = {"status": "AVAILABLE", "Lifecycle_jobs": jobs,
                        "original_operands": [states[key] for key in sorted(status_calls)],
                        "sql_work": "UNAVAILABLE: no exact original State StatementWork supplied"}
            result["adjusted_without_status_state_jobs"] = {"owner": without_status_owner, class_count: without_status_classes,
                        "scope": "count-only floor view; original public Status jobs retained in raw and Resources-adjusted views; SQL/time unchanged"}
        else:
            result["status_state_attribution"] = {"status": "UNAVAILABLE", "reason": "typed original Status.local outcome unavailable; no guessed job/SQL subtraction"}
        for key, fields in (("store",STORE),("cache",CACHE_COUNTERS)):
            if key in before and key in end:
                result["raw"][key] = difference(before[key],end[key],fields)
        if "reader" in before and "reader" in end:
            reader_counter = "requests" if "requests" in before["reader"] else "grants"
            require(reader_counter in end["reader"], "mixed reader schemas in one interval")
            result["raw"]["reader"] = difference(before["reader"],end["reader"],(reader_counter,))
        if "native" in before and "native" in end and before["native"]["owner_id"] == end["native"]["owner_id"] and "opcodes" in before and "opcodes" in end:
            left, right = before["opcodes"], end["opcodes"]
            if before["native"]["detached"] and not end["native"]["detached"]:
                # Opcode counters belong to one connection and start at zero.
                # The before endpoint's connection had already detached, so the
                # end endpoint's own counters are the whole interval.
                require(all(last != 2**64-1 for last in right["by_opcode"]), "opcode counters saturated")
                result["raw"]["opcodes"] = {"by_opcode": list(right["by_opcode"]),
                        "disposition": difference(dict.fromkeys(DIRECT_DISPOSITION if direct_mode else OPCODE_DISPOSITION,0),right["disposition"],DIRECT_DISPOSITION if direct_mode else OPCODE_DISPOSITION),
                        "scope": "a later mount connection counted from its own start; the before endpoint's connection was detached"}
            else:
                require(all(last >= first and last != 2**64-1 and first != 2**64-1 for first,last in zip(left["by_opcode"],right["by_opcode"])), "opcode counters decreased or saturated")
                result["raw"]["opcodes"] = {"by_opcode": [last-first for first,last in zip(left["by_opcode"],right["by_opcode"])],
                        "disposition": difference(left["disposition"],right["disposition"],DIRECT_DISPOSITION if direct_mode else OPCODE_DISPOSITION),
                        "scope": "one original mount connection; control diagnostic counts are not FUSE requests"}
    except (ValueError, KeyError, TypeError, IndexError) as error:
        result["status"] = "UNAVAILABLE"
        result["reason"] = str(error)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--numeric-validation", type=Path, required=True)
    parser.add_argument("--before-identity", required=True, help="JSON [daemon words, scope words, call]")
    parser.add_argument("--end-identity", required=True, help="JSON [daemon words, scope words, call]")
    parser.add_argument("--exclusive-observer-scope", action="store_true")
    parser.add_argument("--control-correlation", type=Path, help="original validated successful send ranges with typed Status attribution")
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(args.numeric_validation.read_text())
    require(original.get("status") == "PASS", "complete validated original numeric framing required")
    correlation = json.loads(args.control_correlation.read_text())["calls"] if args.control_correlation else None
    result = phase_counts(original["sections"], json.loads(args.before_identity), json.loads(args.end_identity),
                          exclusive_observer_scope=args.exclusive_observer_scope, label=args.label, control_correlation=correlation)
    with args.output.open("x") as stream:
        json.dump(result,stream,indent=2,sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "output": str(args.output), "reason": result.get("reason")}))


if __name__ == "__main__":
    main()
