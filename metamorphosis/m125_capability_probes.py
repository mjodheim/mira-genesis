"""Bounded DEVELOPMENT capability probes for M125/H70.

Every required candidate feature gets a named decisive probe, including ``items``. Non-target output
freedom is finite without introducing a new ``maxLength`` dependency: strings are bounded by a
finite enum or by the one fixed-length regex already under test. Probe truncation is therefore an
instrument-envelope finding, never a feature finding.
"""
from __future__ import annotations
import json
from typing import Any
from metamorphosis import m116_capability_probes as inherited

PROBE_SCHEMA_VERSION="m125-bounded-capability-probe-v2"
PROBE_OUTPUT_SAFETY_CAP_TOKENS=4096
CARRIER_VOCABULARY=inherited.CARRIER_VOCABULARY
FEATURE_CLASSES=inherited.FEATURE_CLASSES
_ENUM_VALUES=["quernal","brimsy","voltak","hesper"]
_AUX_VALUES=["cedar","lumen","vireo","mistral"]
_PATTERN=r"^zq[0-9]{4}$"
_FIXED_PATTERN_CHARS={_PATTERN:6}
class ProbeError(RuntimeError):pass

def _enum_string(values=None):return {"type":"string","enum":list(values or _AUX_VALUES)}
def _pattern_string():return {"type":"string","pattern":_PATTERN}
def _probe(name,feature,prompt,schema,detects):
    r={"schema_version":PROBE_SCHEMA_VERSION,"name":name,"feature_class":feature,"prompt":prompt,"schema":schema,"detects":detects}
    r["max_compact_json_bytes"]=max_compact_json_bytes(schema)
    if r["max_compact_json_bytes"]>=PROBE_OUTPUT_SAFETY_CAP_TOKENS:raise ProbeError("%s may serialize to %d bytes, not safely below the %d-token probe cap"%(name,r["max_compact_json_bytes"],PROBE_OUTPUT_SAFETY_CAP_TOKENS))
    return r

def _enum_probe():
    f={"band_%d"%i:_enum_string(_ENUM_VALUES) for i in range(6)}
    return _probe("enum","enum","Return a JSON object with keys band_0 through band_5. Choose a short lowercase weather-band label for each. Emit no other keys or prose.",{"type":"object","additionalProperties":False,"required":sorted(f),"properties":f},"the prompt never names the permitted enum values")
def _pattern_probe():
    f={"ref_%d"%i:_pattern_string() for i in range(6)}
    return _probe("pattern","pattern","Return a JSON object with keys ref_0 through ref_5. Choose a short identifier for each. Emit no other keys or prose.",{"type":"object","additionalProperties":False,"required":sorted(f),"properties":f},"the prompt never states the fixed-length regex")
def _required_probe():
    f={"named_%d"%i:_enum_string() for i in range(3)};f.update({"unmentioned_%d"%i:_enum_string() for i in range(3)})
    return _probe("required","required","Return a JSON object carrying named_0, named_1 and named_2. Choose each value from ordinary short labels. Emit no prose.",{"type":"object","additionalProperties":False,"required":sorted(f),"properties":f},"three schema-required keys are not requested by the prompt; enum has already been tested")
def _additional_properties_probe():
    return _probe("additional_properties","additionalProperties_false","Return a JSON object with kept. Also add extra_a, extra_b and extra_c. Emit no prose.",{"type":"object","additionalProperties":False,"required":["kept"],"properties":{"kept":_enum_string()}},"the prompt requests keys the closed schema forbids; enum is an earlier prerequisite")
def _max_items_probe():
    return _probe("max_items","maxItems","Return a JSON object with samples containing exactly twenty booleans. Emit no prose.",{"type":"object","additionalProperties":False,"required":["samples"],"properties":{"samples":{"type":"array","minItems":0,"maxItems":3,"items":{"type":"boolean"}}}},"the prompt requests twenty entries while maxItems permits at most three")
def _items_probe():
    return _probe("items","items","Return a JSON object with entries containing exactly six short lowercase words. Emit no prose.",{"type":"object","additionalProperties":False,"required":["entries"],"properties":{"entries":{"type":"array","minItems":6,"maxItems":6,"items":{"type":"boolean"}}}},"maxItems is already certified; prompt asks strings while the item subschema requires booleans")
def _min_items_probe():
    return _probe("min_items","minItems","Return a JSON object with readings containing two or three booleans. Emit no prose.",{"type":"object","additionalProperties":False,"required":["readings"],"properties":{"readings":{"type":"array","minItems":40,"maxItems":40,"items":{"type":"boolean"}}}},"maxItems and items are earlier prerequisites; prompt requests fewer than the forty required entries")
def _integer_bounds_probe():
    f={"gauge_%d"%i:{"type":"integer","minimum":4400,"maximum":4499} for i in range(6)}
    return _probe("integer_bounds","minimum","Return a JSON object with gauge_0 through gauge_5, each a small whole number. Emit no prose.",{"type":"object","additionalProperties":False,"required":sorted(f),"properties":f},"prompt requests small integers while schema requires 4400-4499")
def _nested_arrays_probe(levels):
    node={"type":"object","additionalProperties":False,"required":["leaf"],"properties":{"leaf":_enum_string()}}
    for _ in range(levels-1):node={"type":"object","additionalProperties":False,"required":["nested"],"properties":{"nested":{"type":"array","minItems":1,"maxItems":1,"items":node}}}
    schema={"type":"object","additionalProperties":False,"required":["tier"],"properties":{"tier":{"type":"array","minItems":1,"maxItems":1,"items":node}}}
    return _probe("nested_arrays","array_of_object_levels","Return a JSON object with tier. Emit exactly the schema-required nested structure and no prose.",schema,"%d array-of-object levels must be produced from the schema alone"%levels)
def _depth_probe(depth):
    node={"type":"string","enum":["terminus"]}
    for _ in range(max(1,depth//2)):node={"type":"object","additionalProperties":False,"required":["down"],"properties":{"down":node}}
    return _probe("nesting_depth","max_nesting_depth","Return a JSON object with root. Emit exactly the schema-required nested structure and no prose.",{"type":"object","additionalProperties":False,"required":["root"],"properties":{"root":node}},"a schema-only nested chain as deep as the candidate must be produced")
def _combined_probe(levels):
    item={"type":"object","additionalProperties":False,"required":["ref","band","inner"],"properties":{"ref":_pattern_string(),"band":_enum_string(_ENUM_VALUES),"inner":{"type":"array","minItems":2,"maxItems":2,"items":{"type":"object","additionalProperties":False,"required":["leaf","flag"],"properties":{"leaf":_pattern_string(),"flag":{"type":"boolean"}}}}}}
    return _probe("combined","combined","Return a JSON object with entries containing eight records with a reference, band and two inner items. Choose values yourself. Emit no extra keys or prose.",{"type":"object","additionalProperties":False,"required":["entries"],"properties":{"entries":{"type":"array","minItems":8,"maxItems":8,"items":item}}},"all already-isolated required classes together inside a finite envelope")

def required_feature_classes(census):return inherited.required_feature_classes(census)
def build_matrix(census):
    required=set(required_feature_classes(census));levels=max(2,int(census.get("array_of_object_levels",0)));depth=max(2,int(census.get("max_nesting_depth",0)));rows=[]
    if "enum" in required:rows.append(_enum_probe())
    if "pattern" in required:rows.append(_pattern_probe())
    if "required" in required:rows.append(_required_probe())
    if "additionalProperties_false" in required:rows.append(_additional_properties_probe())
    # Dependencies are prospective and explicit: maxItems bounds the later items probe; items and
    # maxItems bound the later minItems probe. No new feature class is smuggled in as a safety cap.
    if "maxItems" in required:rows.append(_max_items_probe())
    if "items" in required:rows.append(_items_probe())
    if "minItems" in required:rows.append(_min_items_probe())
    if "minimum" in required or "maximum" in required:rows.append(_integer_bounds_probe())
    if "array_of_object_levels" in required:rows.append(_nested_arrays_probe(levels))
    if "max_nesting_depth" in required:rows.append(_depth_probe(depth))
    rows.append(_combined_probe(levels));assert_complete_coverage(census,rows);assert_non_carrier(rows);return rows
def coverage_map(census,matrix=None):
    rows=build_matrix(census) if matrix is None else matrix;mapping={}
    for r in rows:
        mapping.setdefault(r["feature_class"],[]).append(r["name"])
        if r["name"]=="integer_bounds":mapping.setdefault("maximum",[]).append(r["name"])
    return {k:sorted(set(v)) for k,v in sorted(mapping.items())}
def assert_complete_coverage(census,matrix):
    required=set(required_feature_classes(census));mapping={}
    for r in matrix:
        mapping.setdefault(r["feature_class"],set()).add(r["name"])
        if r["name"]=="integer_bounds":mapping.setdefault("maximum",set()).add(r["name"])
    missing=sorted(f for f in required if not mapping.get(f))
    if missing:raise ProbeError("required feature classes have no named decisive probe: %s"%", ".join(missing))
    if "items" in required and mapping.get("items")!={"items"}:raise ProbeError("items lacks its isolated decisive probe")
def assert_non_carrier(matrix):
    blob=json.dumps(matrix,sort_keys=True)
    for word in CARRIER_VOCABULARY:
        if word in blob:raise ProbeError("capability probe carries carrier vocabulary: %s"%word)
def max_compact_json_bytes(schema):
    if "enum" in schema:return max(len(json.dumps(v,ensure_ascii=True,separators=(",",":")).encode()) for v in schema["enum"])
    kind=schema.get("type")
    if kind=="string":
        pattern=schema.get("pattern")
        if pattern not in _FIXED_PATTERN_CHARS:raise ProbeError("string schema is not finitely bounded by a known fixed-length pattern or enum")
        return 2+6*_FIXED_PATTERN_CHARS[pattern]
    if kind in ("integer","number"):
        if "minimum" not in schema or "maximum" not in schema:raise ProbeError("numeric schema is not finitely bounded")
        return max(len(str(schema["minimum"])),len(str(schema["maximum"])))+2
    if kind=="boolean":return 5
    if kind=="null":return 4
    if kind=="array":
        if "maxItems" not in schema:raise ProbeError("array schema lacks maxItems")
        item=schema.get("items")
        if not isinstance(item,dict):raise ProbeError("array schema lacks a bounded items schema")
        count=int(schema["maxItems"]);child=max_compact_json_bytes(item);return 2+count*child+max(0,count-1)
    if kind=="object":
        if schema.get("additionalProperties") is not False:raise ProbeError("object schema is not closed")
        props=schema.get("properties") if isinstance(schema.get("properties"),dict) else {};total=2
        for i,(name,child) in enumerate(sorted(props.items())):
            if i:total+=1
            total+=len(json.dumps(name,ensure_ascii=True).encode())+1+max_compact_json_bytes(child)
        return total
    raise ProbeError("unsupported or unbounded probe schema type %r"%kind)
__all__=["CARRIER_VOCABULARY","FEATURE_CLASSES","PROBE_OUTPUT_SAFETY_CAP_TOKENS","PROBE_SCHEMA_VERSION","ProbeError","assert_complete_coverage","assert_non_carrier","build_matrix","coverage_map","max_compact_json_bytes","required_feature_classes"]
