from dataclasses import dataclass
from typing import List, Dict, Optional
import re

RAM_EL_SIZE = 16
ROM_EL_SIZE = 32

# === Structures de base ===

class GateType:
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"
    NXOR = "NXOR"
    NOT = "NOT"
    CONST = "CONST"
    MUX = "MUX"
    CONCAT = "CONCAT"
    INDEX = "INDEX"
    SUB = "SUB"
    BUF = "BUF"
    LOAD = "LOAD"
    STORE = "STORE"
    ROM = "ROM"

@dataclass
class GateIR:
    id: int
    type: str
    output: int
    input1: int = 0
    input2: int = 0
    input3: int = 0
    size: int = 1
    enabled_if : int = -1
    const_value: Optional[int] = None

@dataclass
class Signal:
    name: str
    index: int
    size: int = 1

# === Compiler ===


import re

import re

def _interpolate(line: str, context: dict) -> str:
    return re.sub(r"\{([^{}]+)\}", lambda m: str(eval(m.group(1), {}, context)), line)

def expand_macros(lines: list[str]) -> list[str]:
    def process_block(block: list[str], context: dict) -> list[str]:
        expanded = []
        i = 0

        while i < len(block):
            raw_line = block[i]
            line = raw_line.strip()

            if line.upper().startswith("FOR "):
                match = re.match(r"FOR (\w+) IN (\d+) TO (\d+):", line)
                if not match:
                    raise ValueError(f"Syntaxe FOR invalide : {line}")
                var, start, end = match.group(1), int(match.group(2)), int(match.group(3))
                inner_block = []
                i += 1

                depth = 1
                while i < len(block) and depth > 0:
                    line_check = block[i].strip()
                    if line_check.upper().startswith("FOR "):
                        depth += 1
                    elif line_check.upper() == "END":
                        depth -= 1
                        if depth == 0:
                            break
                    if depth > 0:
                        inner_block.append(block[i])
                    i += 1
                if depth != 0:
                    raise ValueError("Bloc FOR sans END")

                for val in range(start, end + 1):
                    new_context = context.copy()
                    new_context[var] = val
                    expanded.extend(process_block(inner_block, new_context))

            elif line.upper().startswith("IF "):
                cond_expr = line[3:].rstrip(":")
                condition_true = eval(cond_expr, {}, context)
                buffer = []
                else_buffer = []
                i += 1

                while i < len(block):
                    line_if = block[i].strip()
                    if line_if.upper() == "ELSE:":
                        i += 1
                        break
                    elif line_if.upper() == "ENDIF":
                        break
                    buffer.append(block[i])
                    i += 1

                while i < len(block):
                    line_else = block[i].strip()
                    if line_else.upper() == "ENDIF":
                        break
                    else_buffer.append(block[i])
                    i += 1

                if condition_true:
                    expanded.extend([_interpolate(l, context) for l in buffer])
                else:
                    expanded.extend([_interpolate(l, context) for l in else_buffer])
                i += 1

            else:
                if line.upper() not in {"END", "ENDIF", "ELSE:"}:
                    expanded.append(_interpolate(raw_line, context))
                i += 1

        return expanded

    return process_block(lines, {})




class NetlistCompiler:
    def __init__(self):
        self.signal_table: Dict[str, Signal] = {}
        self.signal_counter = 0
        self.ir: List[GateIR] = []
        self.ir_id = 0
        self.const_cache: Dict[str, int] = {}  # valeur binaire -> index signal
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.index_cache: Dict[tuple, Signal] = {} 
        self.enabled_index = -1

    def get_or_create_signal(self, name: str, size: int = 1) -> Signal:
        if name not in self.signal_table:
            sig = Signal(name, self.signal_counter, size)
            self.signal_table[name] = sig
            self.signal_counter += 1
        return self.signal_table[name]

    def create_const(self, value: str) -> Signal:
        if value in self.const_cache:
            index = self.const_cache[value]
            return Signal(f"__const_{value}", index, len(value))
        sig = self.get_or_create_signal(f"__const_{value}", size=len(value))
        self.ir.append(GateIR(
            id=self.ir_id,
            type=GateType.CONST,
            output=sig.index,
            size=sig.size,
            const_value=int(value,2),
            enabled_if=self.enabled_index
        ))
        self.const_cache[value] = sig.index
        self.ir_id += 1
        return sig


    def parse_arg(self, token: str, size=1) -> Signal:
        # Constante binaire
        if set(token).issubset({"0", "1"}):
            return self.create_const(token)

        # Index automatique : A[3]
        m = re.match(r"([A-Za-z_][A-Za-z_0-9]*)\[(\d+)\]", token)
        if m:
            base, bit_index = m.group(1), int(m.group(2))
            key = (base, bit_index)
            if key in self.index_cache:
                return self.index_cache[key]

            input_sig = self.get_or_create_signal(base)
            tmp_name = f"__idx_{base}_{bit_index}"
            tmp_sig = self.get_or_create_signal(tmp_name, size=1)

            self.ir.append(GateIR(
                id=self.ir_id,
                type=GateType.INDEX,
                output=tmp_sig.index,
                input1=input_sig.index,
                size=1,
                const_value=bit_index,
                enabled_if=self.enabled_index
            ))
            self.ir_id += 1
            self.index_cache[key] = tmp_sig
            return tmp_sig

        # Nom de signal classique
        return self.get_or_create_signal(token,size)


    def compile_line(self, line: str):
        
        line = line.strip()
        if not line or line.startswith("#"):
            return
        
        if line.startswith("GHOST_END"):
            self.enabled_index = -1
            return
        
        if line.startswith("GHOST"):
            parts = line.split()
            if len(parts) != 2:
                raise ValueError(f"Ligne GHOST invalide : '{line}'")
            _, name = parts
            self.enabled_index = self.get_or_create_signal(name).index
            return

        if line.upper().startswith("INPUT"):
            _, *items = line.split()
            for item in items:
                if ":" in item:
                    name, size_str = item.split(":")
                    size = int(size_str)
                else:
                    name = item
                    size = 1  # par défaut
                self.inputs.append(name)
                self.get_or_create_signal(name, size)
            return

        if line.upper().startswith("OUTPUT"):
            _, *names = line.split()
            for name in names:
                self.outputs.append(name)
                self.get_or_create_signal(name)
            return

        # Séparation destination et expression
        if "=" not in line:
            raise ValueError(f"Ligne invalide : pas de '=' → {line}")

        dest, expr = [s.strip() for s in line.split("=", 1)]
        parts = expr.split()
        if not parts:
            raise ValueError(f"Ligne invalide ou vide après '=' : {line}")

        op = parts[0].upper()
        args = parts[1:]

        # Syntaxe spéciale : BUF avec override de taille
        if op.startswith("BUF:"):
            try:
                override_size = int(op.split(":")[1])
            except ValueError:
                raise ValueError(f"Taille invalide dans BUF: → {op}")
            op = GateType.BUF
            in1 = self.parse_arg(args[0],override_size)
            dest_sig = self.get_or_create_signal(dest, size=override_size)
            self.ir.append(GateIR(
                id=self.ir_id,
                type=op,
                output=dest_sig.index,
                input1=in1.index,
                input2=0,
                input3=0,
                size=override_size,
                enabled_if=self.enabled_index
            ))
            self.ir_id += 1
            return


        # Vérification du nombre minimal d’arguments attendus
        min_args_required = {
            "AND": 2, "OR": 2, "XOR": 2, "NAND": 2, "NOR": 2, "NXOR": 2,
            "NOT": 1, "MUX": 3,
            "CONCAT": 2, "SUB": 3, "INDEX": 2,
            "CONST": 1, "BUF" : 1, "LOAD" : 1, "STORE" : 2
        }.get(op, 1)

        if len(args) < min_args_required:
            raise ValueError(f"Ligne '{line}' → trop peu d'arguments pour {op} (requis : {min_args_required})")


        if op == GateType.CONST:
            dest_sig = self.get_or_create_signal(dest, size=len(args[0]))
            self.ir.append(GateIR(
                id=self.ir_id,
                type=GateType.CONST,
                output=dest_sig.index,
                size=dest_sig.size,
                const_value=int(args[0], 2),
                enabled_if=self.enabled_index
            ))
            self.ir_id += 1
            return


        if op == GateType.CONCAT and len(args) > 2:
            # concat multiple : expansion récursive
            concat_signals = [self.parse_arg(tok) for tok in args]
            tmp_name = f"__tmp_concat_{self.ir_id}"
            tmp_sig = concat_signals[0]
            for i in range(1, len(concat_signals)-1):
                new_tmp_name = f"{tmp_name}_{i}"
                new_sig = self.get_or_create_signal(new_tmp_name, size=tmp_sig.size + concat_signals[i].size)
                self.ir.append(GateIR(
                    id=self.ir_id,
                    type=GateType.CONCAT,
                    output=new_sig.index,
                    input1=tmp_sig.index,
                    input2=concat_signals[i].index,
                    size=new_sig.size,
                    const_value=concat_signals[i].size,
                    enabled_if=self.enabled_index
                ))
                self.ir_id += 1
                tmp_sig = new_sig

            # dernière concat vers dest
            final_input = concat_signals[-1]
            inferred_size = tmp_sig.size + final_input.size
            dest_sig = self.get_or_create_signal(dest, size=inferred_size)
            self.ir.append(GateIR(
                id=self.ir_id,
                type=GateType.CONCAT,
                output=dest_sig.index,
                input1=tmp_sig.index,
                input2=final_input.index,
                size=dest_sig.size,
                const_value=final_input.size,
                enabled_if=self.enabled_index
            ))
            self.ir_id += 1
            return

        in1 = self.parse_arg(args[0]) if len(args) > 0 else None
        if op != GateType.INDEX and op!=GateType.SUB:
            in2 = self.parse_arg(args[1]) if len(args) > 1 else None
        else:
            in2 = None
        in3 = self.parse_arg(args[2]) if len(args) > 2 and op == GateType.MUX else None

        constante = None
        

        # inférence de taille à partir des entrées
        sizes = [s.size for s in (in1, in2, in3) if s]

        if op==GateType.STORE:
            assert sizes[0]==RAM_EL_SIZE, f"error ligne {line} une adresse RAM doit etre de taille 16"
            self.ir.append(GateIR(
            id=self.ir_id,
            type=op,
            output=-1,
            input1=in1.index,
            input2=in2.index,
            input3=0,
            size=RAM_EL_SIZE,
            const_value=constante,
            enabled_if=self.enabled_index
            ))
            return


        if op==GateType.CONCAT:
            inferred_size = sizes[0]+sizes[1]
            constante = sizes[1]
        elif op==GateType.INDEX:
            inferred_size = 1
            constante = int(args[1])
        elif op==GateType.SUB:
            inferred_size = int(args[2]) - int(args[1])+1
            constante = int(args[1])
        elif op == GateType.BUF and in1:
            inferred_size = in1.size
        elif op == GateType.LOAD:
            assert sizes[0]==RAM_EL_SIZE, f"error ligne {line} une adresse RAM doit etre de taille 16"
            inferred_size = RAM_EL_SIZE
        elif op == GateType.ROM:
            assert sizes[0]==RAM_EL_SIZE, f"error ligne {line} une adresse ROM doit etre de taille 16"
            inferred_size = ROM_EL_SIZE
        else:
            inferred_size = max(sizes) if sizes else 1

        dest_sig = self.get_or_create_signal(dest, size=inferred_size)

        self.ir.append(GateIR(
            id=self.ir_id,
            type=op,
            output=dest_sig.index,
            input1=in1.index if in1 else 0,
            input2=in2.index if in2 else 0,
            input3=in3.index if in3 else 0,
            size=dest_sig.size,
            const_value=constante,
            enabled_if=self.enabled_index
        ))
        self.ir_id += 1


    def compile_netlist(self, lines: List[str]) -> List[GateIR]:
        self.signal_table.clear()
        self.signal_counter = 0
        self.ir.clear()
        self.ir_id = 0
        self.const_cache.clear()
        self.inputs.clear()
        self.outputs.clear()

        for line in expand_macros(lines):
            self.compile_line(line)
        for i in range(len(self.inputs)):
            self.inputs[i] = str(self.signal_table[self.inputs[i]].index)
        for i in range(len(self.outputs)):
            self.outputs[i] = str(self.signal_table[self.outputs[i]].index)
        return self.ir

    def generate_ir_string(self, lines: List[str]) -> str:
        self.compile_netlist(lines)
        result = []
        result.append(f"# INPUTS: {', '.join(self.inputs)}")
        result.append(f"# OUTPUTS: {', '.join(self.outputs)}")
        result.append(f"# SIGNALS: {self.signal_counter}")
        for instr in self.ir:
            result.append(str(instr))
        return "\n".join(result)+"\n"