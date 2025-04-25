import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit,
    QVBoxLayout, QFileDialog, QLabel, QHBoxLayout
)
from netlist_compiler import NetlistCompiler
from assembler_compiler import compile_assembler_to_rom

import subprocess

class NetlistGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netlist Compiler")
        self.resize(600, 400)

        self.file_path = "netlists/cpu.ir"
        self.rom_path = None
        self.text = ""
        self.ir = []

        self.label = QLabel(self.file_path)
        self.romlabel = QLabel("Aucune rom selectionée")
        self.btn_select = QPushButton("Choisir Netlist")
        self.btn_compile = QPushButton("Compiler")
        self.btn_export = QPushButton("Exporter l'IR")
        self.btn_execute = QPushButton("Exécuter")
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_select)
        button_layout.addWidget(self.btn_compile)
        button_layout.addWidget(self.btn_export)
        button_layout.addWidget(self.btn_execute)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.romlabel)
        layout.addLayout(button_layout)
        layout.addWidget(self.text_output)
        self.setLayout(layout)

        self.btn_select.clicked.connect(self.select_file)
        self.btn_compile.clicked.connect(self.compile_file)
        self.btn_export.clicked.connect(self.export_ir)
        self.btn_execute.clicked.connect(self.run_simulator)

        self.btn_rom_choose = QPushButton("Choisir rom")
        button_layout.addWidget(self.btn_rom_choose)
        self.btn_rom_choose.clicked.connect(self.choose_rom)

        self.btn_assemble = QPushButton("Compiler assembleur")
        button_layout.addWidget(self.btn_assemble)
        self.btn_assemble.clicked.connect(self.compile_assembler)

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier Netlist", "", "Netlist files (*.net *.ir)")
        if path:
            self.file_path = path
            self.label.setText(f"Fichier : {path}")

    def compile_file(self):
        if not self.file_path:
            self.text_output.setText("Veuillez d'abord sélectionner un fichier.")
            return
        if self.file_path[-4:] != ".net":
            self.text_output.setText("Veuillez sélectionner un fichier .net")
            return
        try:
            with open(self.file_path, 'r') as f:
                lines = f.readlines()
            compiler = NetlistCompiler()
            self.text = compiler.generate_ir_string(lines)
            self.text_output.setText(self.text)
        except Exception as e:
            self.text_output.setText(f"Erreur lors de la compilation : {e}")

    def export_ir(self):
        if not self.text:
            self.text_output.setText("Veuillez compiler un fichier avant d'exporter.")
            return
        path = self.file_path[:-3]+"ir"
        if path:
            try:
                with open(path, 'w') as f:
                    f.write(self.text)
                self.text_output.setText(f"IR exportée dans : {path}")
                self.file_path = path
                self.label.setText(f"Fichier : {path}")
            except Exception as e:
                self.text_output.setText(f"Erreur lors de l'export : {e}")
                return

    def run_simulator(self):
        if self.file_path == None or self.file_path[-3:]!=".ir":
            self.text_output.setText("Can only execute IR files")
            return
        if self.rom_path == None or self.rom_path[-4:]!=".rom":
            self.text_output.setText("Must have a ROM program to execute")
            return
        executable = "./simulateur.exe"
        print("coucou")
        try:
            subprocess.run([executable, self.file_path, self.rom_path], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'exécution du simulateur : {e}")

    def choose_rom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un fichier assembleur", "", "Assembler files (*.asb *.rom)")
        if not path:
            return
        if not path.endswith(".asb") and not path.endswith(".rom"):
            self.text_output.setText("Veuillez sélectionner un fichier .asb ou .rom")
            return
        self.rom_path = path
        self.romlabel.setText("ROM sélectionée : "+self.rom_path)

    def compile_assembler(self):
        try:
            binary_lines = compile_assembler_to_rom(self.rom_path)
            output_path = self.rom_path[:-4] + ".rom"
            with open(output_path, 'w') as f:
                for line in binary_lines:
                    f.write(line + '\n')
            self.text_output.setText(f"Compilation terminée : {output_path}")
            self.rom_path = output_path
            self.romlabel.setText("ROM sélectionée : "+self.rom_path)
        except Exception as e:
            self.text_output.setText(f"Erreur lors de la compilation assembleur : {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    gui = NetlistGUI()
    gui.show()
    sys.exit(app.exec())