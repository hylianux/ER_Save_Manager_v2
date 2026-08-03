#!/usr/bin/env python3
"""
Locate the real arche_type (starting class) byte in an Elden Ring save.

Structure of PlayerGameData, per the ER-Save-Editor field order:
    character_name : 0x10 * u16   (0x20 bytes, UTF-16LE, null padded)
    _pad           : 0x02 bytes
    gender         : u8   (0 or 1)
    arche_type     : u8   (0-9)

So the class byte always sits at  name_start + 0x23,  regardless of patch.

Usage:  python find_class_offset.py /path/to/ER0000.co2
"""
import sys
import hexedit

CLASSES = ["Vagabond", "Warrior", "Hero", "Bandit", "Astrologer",
           "Prophet", "Confessor", "Samurai", "Prisoner", "Wretch"]
LEGACY_POS = 42165          # the value hardcoded in hexedit.set_starting_class
NAME_LEN = 0x20             # 16 UTF-16 code units
CLASS_DELTA = 0x20 + 0x02 + 0x01   # name + pad + gender  -> 0x23


def candidates(slot_bytes, name):
    """Yield every plausible arche_type offset for `name` inside this slot."""
    needle = name.encode("utf-16-le")
    if not needle:
        return
    idx = slot_bytes.find(needle)
    while idx != -1:
        pos = idx + CLASS_DELTA
        if pos < len(slot_bytes):
            gender = slot_bytes[pos - 1]
            klass = slot_bytes[pos]
            if gender in (0, 1) and klass < len(CLASSES):
                yield pos, klass, gender
        idx = slot_bytes.find(needle, idx + 2)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python find_class_offset.py /path/to/save.co2")
    path = sys.argv[1]

    names = hexedit.get_names(path)
    if names is False:
        sys.exit(f"could not read {path}")
    slots = hexedit.get_slot_ls(path)

    print(f"save: {path}\n")
    for i, name in enumerate(names):
        label = f"slot {i+1}"
        if name is None:
            print(f"{label}: <empty>")
            continue

        cs = slots[i]
        legacy = cs[LEGACY_POS] if LEGACY_POS < len(cs) else None
        legacy_txt = (CLASSES[legacy] if legacy is not None and legacy < 10
                      else f"?? ({legacy})")
        print(f"{label}: {name!r}")
        print(f"    legacy offset {LEGACY_POS}: {legacy} -> {legacy_txt}")

        found = list(candidates(cs, name))
        if not found:
            print("    structural search: no match "
                  "(name may differ inside the slot)")
        for pos, klass, gender in found:
            delta = pos - LEGACY_POS
            print(f"    structural offset {pos}: {klass} -> {CLASSES[klass]}"
                  f"   (gender={gender}, delta vs legacy {delta:+d})")
        print()


if __name__ == "__main__":
    main()
