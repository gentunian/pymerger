import ast
import os
from collections import defaultdict
from typing import List, Set, Dict

class DependencySorter:
    def __init__(self, files: List[str], base_dir: str = ""):
        self.files = files
        self.base_dir = base_dir
        self.module_to_file: Dict[str, str] = {}
        self.dep_graph: Dict[str, Set[str]] = defaultdict(set)
        self._build_module_mapping()

    def _build_module_mapping(self):
        """Map full module names to file paths."""
        for filepath in self.files:
            rel_path = os.path.relpath(filepath, self.base_dir) if self.base_dir else filepath
            module_name = rel_path.replace(os.sep, '.').rstrip('.py')
            self.module_to_file[module_name] = filepath

    def _get_imports_from_file(self, filepath: str) -> Set[str]:
        """Extract full local module dependencies from a file."""
        dependencies = set()
        module_name = next(k for k, v in self.module_to_file.items() if v == filepath)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        full_module = name.name
                        if full_module in self.module_to_file:
                            dependencies.add(full_module)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module
                    if module and module in self.module_to_file:
                        dependencies.add(module)
                    # Handle relative imports (e.g., '.support.file_reader')
                    elif module and node.level > 0:
                        # Convert relative to absolute based on current module
                        parts = module_name.split('.')
                        level = node.level
                        if level <= len(parts):
                            base = '.'.join(parts[:-level]) if level > 0 else ''
                            full_module = f"{base}.{module}" if base else module
                            if full_module in self.module_to_file:
                                dependencies.add(full_module)

        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

        return dependencies

    def _build_dependency_graph(self):
        """Build dependency graph for all files."""
        for filepath in self.files:
            module_name = next(k for k, v in self.module_to_file.items() if v == filepath)
            dependencies = self._get_imports_from_file(filepath)
            self.dep_graph[module_name] = dependencies

    def _topological_sort(self) -> List[str]:
        """Sort modules: least dependent first, most dependent last."""
        visited = set()
        temp_mark = set()
        sorted_modules = []

        def visit(node: str):
            if node in temp_mark:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node not in visited:
                temp_mark.add(node)
                for dep in self.dep_graph[node]:
                    if dep in self.module_to_file:
                        visit(dep)
                temp_mark.remove(node)
                visited.add(node)
                sorted_modules.append(node)

        for module in self.module_to_file.keys():
            if module not in visited:
                visit(module)

        return sorted_modules

    def get_sorted_files(self) -> List[str]:
        """Return files sorted from least to most dependent."""
        self._build_dependency_graph()
        try:
            sorted_modules = self._topological_sort()
            return [self.module_to_file[module] for module in sorted_modules]
        except ValueError as e:
            print(f"Error: {e}")
            return []
