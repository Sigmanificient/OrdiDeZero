import re
import os

ALU_OPS = {
    '+': 'ADD',
    '-': 'SUB',
    '*': 'MUL',
    '&': 'AND',
    '|': 'OR',
    '^': 'XOR',
}

ALU_CODES = {
    'ADD': '00000',
    'SUB': '00001',
    'MUL': '00010',
    'MOV2' : '00011',
    'AND': '00100',
    'OR':  '00101',
    'XOR': '00110',
    'MOV1': '00111',
    'COMP' : '10001',
    'JUMP' : '11000',
    'JUMPE' : '11001',
    'JUMPZ' : '11011',
    'LOAD' : '01100',
    'STORE' : '11100',
    'ROM1' : '01110',
    'ROM2' : '01111',
}

def to_bin(n, bits):
    return format(n & ((1 << bits) - 1), f'0{bits}b')

def to_binary_16bit_signed(value):
    if not (0 <= value < 2**16):
        raise ValueError(f"Immediate {value} out of range for 16-bit unsigned")
    return to_bin(value, 16)

def parse_line(line, directory_path):
    line = line.strip()
    if not line or line.startswith("//"):
        return None
    
    if line=="stop":
        return [('MOV', 'r0', '#0000000000000000'),('STORE', 'r0', 'r0', '#0000000000000000')]
    
    if line.startswith("call "):
        name = line[5:]
        return [('MOV','r15',"next_line2"),('JUMP','r0','r0',name)]
    
    if line=="return":
        return [('JUMP','r0','r0','r15')]
    
    if line=="wait":
        return[('MOV','r0',"#0000000000000001"),('STORE', 'r0', 'r0', '#0000000000000001')]
    
    if line.startswith("rsc "):
        n = line[4:]
        if len(n)==16:
            return [('RSC','0'*16+n)]
        if len(n)==32:
            return [('RSC',n)]
        else:
            return [('RSC','0'*16 + to_binary_16bit_signed(int(n)))]
    
    if line.startswith("include "):
        file = directory_path+"/"+line[8:]
        with open(file) as f:
            contenu = f.read()
        bits = ''.join(c for c in contenu if c in '01')

        # Complète à droite pour que la longueur soit un multiple de 32
        if len(bits) % 32 != 0:
            raise ValueError(f"Les ressources doivent etre par paquets de 32, dans l'include {file}")

        # Découpe en tranches de 32 bits
        resultats = [("RSC", bits[i:i+32]) for i in range(0, len(bits), 32)]
        return resultats
        
    
    m_label = re.match(r'label\s+(\w+)', line, re.IGNORECASE)
    if m_label:
        name = m_label.groups()
        return [('LABEL',name)]
    
    m_load = re.match(r'(\w+)\s*=\s*ram\[(.+)\]', line, re.IGNORECASE)
    if m_load:
        dst, arg = m_load.groups()
        arg = arg.strip()
        if arg.upper().startswith("R"):
            return [('LOAD', dst, 'r0', arg)]
        else:
            try:
                const_val = int(arg)
                const_bin = '#' + to_binary_16bit_signed(const_val)
                return [('LOAD', dst, 'r0', const_bin)]
            except ValueError:
                raise ValueError(f"Invalid memory argument: {arg}")
            
    m_rom1 = re.match(r'(\w+)\s*=\s*rom1\[(.+)\]', line, re.IGNORECASE)
    if m_rom1:
        dst, arg = m_rom1.groups()
        arg = arg.strip()
        if arg.upper().startswith("R"):
            return [('ROM1', dst, 'r0', arg)]
        else:
            try:
                const_val = int(arg)
                const_bin = '#' + to_binary_16bit_signed(const_val)
                return [('ROM1', dst, 'r0', const_bin)]
            except ValueError:
                raise ValueError(f"Invalid memory argument: {arg}")
            
    m_rom2 = re.match(r'(\w+)\s*=\s*rom2\[(.+)\]', line, re.IGNORECASE)
    if m_rom2:
        dst, arg = m_rom2.groups()
        arg = arg.strip()
        if arg.upper().startswith("R"):
            return [('ROM2', dst, 'r0', arg)]
        else:
            try:
                const_val = int(arg)
                const_bin = '#' + to_binary_16bit_signed(const_val)
                return [('ROM2', dst, 'r0', const_bin)]
            except ValueError:
                raise ValueError(f"Invalid memory argument: {arg}")

    m_binary = re.match(r'(\w+)\s*=\s*(\w+)\s*([\+\-\*&\|\^])\s*(\w+)', line)
    if m_binary:
        dest, lhs, op, rhs = m_binary.groups()
        op = ALU_OPS.get(op)
        if not op:
            raise ValueError(f"Unknown operator {op}")
        if rhs.startswith('r'):
            return [(op, dest, lhs, rhs)]  # no constant
        else:
            const_val = int(rhs)
            const_bin = to_binary_16bit_signed(const_val)
            return [(op, dest, lhs, '#' + const_bin)]  # constant case

    m_mov = re.match(r'(\w+)\s*=\s*(\$?\w+)', line)
    if m_mov:
        dest, src = m_mov.groups()
        if src.startswith('r') or src.startswith('n') or src.startswith('$'):
            return [('MOV', dest, src)]
        else:
            if len(src)==16:
                const_bin = "#"+src
            else:
                const_val = int(src)
                const_bin = to_binary_16bit_signed(const_val)
            return [('MOV', dest, '#' + const_bin)]
        
    m_comp = re.match(r'comp\s+(\w+)\s+(\w+)', line, re.IGNORECASE)
    if m_comp:
        dest, src = m_comp.groups()
        if src.startswith('r'):
            return [('COMP', 'r0', dest, src)]
        else:
            const_val = int(src)
            const_bin = to_binary_16bit_signed(const_val)
            return [('COMP', 'r0', dest, '#' + const_bin)]
        
    m_jump = re.match(r'(jump|jumpe|jumpz)\s+(\$?\w+)', line, re.IGNORECASE)
    if m_jump:
        opcode, label = m_jump.groups()
        if label.startswith('r') or label.startswith('$'):
            return [(opcode.upper(), 'r0', 'r0', label)]
        else:
            const_val = int(label)
            const_bin = to_binary_16bit_signed(const_val)
            return [(opcode.upper(), 'r0', 'r0', '#' + const_bin)]
        

    # Écriture mémoire : RAM[argument] = R1
    m_store = re.match(r'ram\[(.+)\]\s*=\s*(\w+)', line, re.IGNORECASE)
    if m_store:
        arg, src = m_store.groups()
        arg = arg.strip()
        if arg.upper().startswith("R"):
            return [('STORE', 'r0', src, arg)]
        else:
            try:
                const_val = int(arg)
                const_bin = '#' + to_binary_16bit_signed(const_val)
                return [('STORE', 'r0', src, const_bin)]
            except ValueError:
                raise ValueError(f"Invalid memory argument: {arg}")


    raise ValueError(f"Syntax error: {line}")

def collect_labels(instructions):
    labels = {}
    address = 0
    for instr in instructions:
        if instr[0] == 'LABEL':
            label_name = instr[1][0]
            labels[label_name] = address
        else:
            address += 1
    return labels


def reg_num(reg):
    if not reg.startswith('r'):
        raise ValueError(f"Invalid register {reg}")
    return int(reg[1:])

def encode_instruction(instr,labels,i):
    if instr[0] == 'LABEL':
        return ""
    elif instr[0]=='RSC':
        return instr[1]
    elif instr[0] == 'MOV':
        if instr[2].startswith("next_line"):
            const = to_binary_16bit_signed(i+int(instr[2][9:]))
            return const + '00' + to_bin(reg_num(instr[1]), 4) + to_bin(0, 4) + ALU_CODES['MOV2'] + '1'
        elif instr[2].startswith('#'):
            const = instr[2][1:]
            return const + '00' + to_bin(reg_num(instr[1]), 4) + to_bin(0, 4) + ALU_CODES['MOV2'] + '1'
        elif instr[2].startswith('$'):
            if not instr[2][1:] in labels:
                raise ValueError("Label '" + instr[2][1:] + "' doesn't exist")
            const = to_binary_16bit_signed(labels[instr[2][1:]])
            return const + '00' + to_bin(reg_num(instr[1]), 4) + to_bin(0, 4) + ALU_CODES['MOV2'] + '1'
        else:
            return '0' * 14 + to_bin(reg_num(instr[2]), 4) + to_bin(reg_num(instr[1]), 4) + to_bin(0, 4) + ALU_CODES['MOV2'] + '0'

    elif len(instr) == 4 and instr[3].startswith('#'):
        # format with constant
        const = instr[3][1:]
        return const + '00' + to_bin(reg_num(instr[1]), 4) + to_bin(reg_num(instr[2]), 4) + ALU_CODES[instr[0]] + '1'
    elif len(instr)==4 and instr[3].startswith('$'):
        if not instr[3][1:] in labels:
            raise ValueError("Label '" + instr[3][1:] + "' doesn't exist")
        const = to_binary_16bit_signed(labels[instr[3][1:]])
        return const + '00' + to_bin(reg_num(instr[1]), 4) + to_bin(reg_num(instr[2]), 4) + ALU_CODES[instr[0]] + '1'
    elif len(instr) == 4:
        # no constant
        return '0' * 14 + to_bin(reg_num(instr[3]), 4) + to_bin(reg_num(instr[1]), 4) + to_bin(reg_num(instr[2]), 4) + ALU_CODES[instr[0]] + '0'
    else:
        raise ValueError(f"Invalid instruction format: {instr}")

def assemble(program,directory_path):
    binary_output = []
    instructions = []
    for i, line in enumerate(program.splitlines()):
        try:
            instr = parse_line(line,directory_path)
            if instr:
                instructions+=instr
        except ValueError as e:
            raise ValueError(f"IR compilation : [Line {i+1}] {e}")
    labels = collect_labels(instructions)
    instructions = [i for i in instructions if i[0] != 'LABEL']
    for i,instr in enumerate(instructions):
        try:
            encoded = encode_instruction(instr,labels,i)
            if encoded != "":
                binary_output.append(encoded)
        except ValueError as e:
            raise ValueError(f"Binary Compilation : [Line {i+1}] {e}")
    return binary_output

def compile_assembler_to_rom(filepath):
    with open(filepath, 'r') as f:
        source = f.read()
    directory_path = os.path.dirname(filepath)
    source += "\nstop\n"
    binary_lines = assemble(source,directory_path)
    return binary_lines

