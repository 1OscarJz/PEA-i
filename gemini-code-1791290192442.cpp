// PEA-i | Programa Estadístico de Análisis de Investigación - UPC (C++17)
// Estructuras: Lista enlazada, Multilista (grupo/investigador -> lista de ids),
// Pila (deshacer) y Cola (productos pendientes de validación).
// Persistencia: datos.pea (mismo formato que la versión Python -> interoperabilidad).
// Compilar: g++ -std=c++17 -o pea PEA_i.cpp

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <map>
#include <vector>
#include <ctime>
#include <iomanip>
#include <cstdlib>

using namespace std;

// ---------------------------------------------------------- Estructuras
template <class T> struct Lista {
    struct N { T d; N* s; };
    N *h = nullptr, *t = nullptr; 
    int n = 0;

    Lista() {}
    Lista(const Lista&) = delete; 
    Lista& operator=(const Lista&) = delete;

    ~Lista() { 
        while (h) { 
            N* x = h; 
            h = h->s; 
            delete x; 
        } 
    }

    void add(T d) { 
        N* x = new N{d, nullptr}; 
        if (t) t->s = x; 
        else h = x; 
        t = x; 
        n++; 
    }

    void addHead(T d) { 
        N* x = new N{d, h}; 
        h = x; 
        if (!t) t = x; 
        n++; 
    }

    bool popHead(T& o) { 
        if (!h) return false; 
        N* x = h; 
        o = x->d; 
        h = x->s; 
        if (!h) t = nullptr; 
        delete x; 
        n--; 
        return true; 
    }

    template <class F> bool del(F f) {
        N *a = nullptr, *x = h;
        while (x) {
            if (f(x->d)) { 
                if (a) a->s = x->s; 
                else h = x->s; 
                if (x == t) t = a; 
                delete x; 
                n--; 
                return true; 
            }
            a = x; 
            x = x->s;
        }
        return false;
    }

    template <class F> T* find(F f) { 
        for (N* x = h; x; x = x->s) 
            if (f(x->d)) return &x->d; 
        return nullptr; 
    }
};

template <class T> struct Pila : Lista<T> { 
    void push(T d) { this->addHead(d); } 
    bool pop(T& o) { return this->popHead(o); } 
};

template <class T> struct Cola : Lista<T> { 
    void encolar(T d) { this->add(d); } 
    bool desencolar(T& o) { return this->popHead(o); } 
};

// ---------------------------------------------------------- Entidades
struct Producto { int id; string titulo, tipo, cat; int anio; bool validado, activo; string ced, grupo; };
struct Investigador { string ced, nombre, cat; bool activo; Lista<int> prods; };
struct Grupo { string cod, nombre, clasif, lider; bool activo; Lista<string> integrantes, plan; Lista<int> prods; };
struct Accion { char tipo; int id; string clave; };   // 'A' alta prod, 'P' toggle prod, 'G' toggle grupo, 'I' toggle inv

Lista<Grupo*> grupos; 
Lista<Investigador*> invs; 
Lista<Producto*> prods;
Pila<Accion> deshacer; 
Cola<int> pendientes; 
int sigId = 1;
const char* ARCHIVO = "datos.pea";

Grupo* G(const string& c) { auto p = grupos.find([&](Grupo* g) { return g->cod == c; }); return p ? *p : nullptr; }
Investigador* I(const string& c) { auto p = invs.find([&](Investigador* i) { return i->ced == c; }); return p ? *p : nullptr; }
Producto* P(int id) { auto p = prods.find([&](Producto* x) { return x->id == id; }); return p ? *p : nullptr; }

int anioActual() { 
    time_t t = time(0); 
    return localtime(&t)->tm_year + 1900; 
}

// ---------------------------------------------------------- CRUD
Grupo* addGrupo(string c, string n, string cl = "", string l = "") {
    if (G(c)) return nullptr; 
    Grupo* g = new Grupo{c, n, cl, l, true}; 
    grupos.add(g); 
    return g;
}

Investigador* addInv(string c, string n, string cat = "") {
    if (Investigador* i = I(c)) return i; 
    Investigador* i = new Investigador{c, n, cat, true}; 
    invs.add(i); 
    return i;
}

bool addMiembro(string cg, string ci) {
    Grupo* g = G(cg); 
    if (!g || !I(ci) || g->integrantes.find([&](string s) { return s == ci; })) return false;
    g->integrantes.add(ci); 
    return true;
}

Producto* addProd(string t, string tipo, string cat, int anio, string ced, string gr, bool val = false, int id = 0, bool encolar = true) {
    if (!id) id = sigId; 
    if (id >= sigId) sigId = id + 1;
    Producto* p = new Producto{id, t, tipo, cat, anio, val, true, ced, gr}; 
    prods.add(p);
    if (G(gr)) G(gr)->prods.add(id);
    if (I(ced)) I(ced)->prods.add(id);
    if (!val && encolar) pendientes.encolar(id);
    deshacer.push({'A', id, ""}); 
    return p;
}

bool delProd(int id) {
    if (!P(id)) return false;
    for (auto n = grupos.h; n; n = n->s) n->d->prods.del([&](int v) { return v == id; });
    for (auto n = invs.h; n; n = n->s) n->d->prods.del([&](int v) { return v == id; });
    pendientes.del([&](int v) { return v == id; });
    Producto* p = P(id); 
    prods.del([&](Producto* x) { return x->id == id; }); 
    delete p; 
    return true;
}

bool delGrupo(string c) {
    Grupo* g = G(c); 
    if (!g) return false;
    while (g->prods.h) delProd(g->prods.h->d);
    grupos.del([&](Grupo* x) { return x->cod == c; }); 
    delete g; 
    return true;
}

bool delInv(string c) {
    Investigador* i = I(c); 
    if (!i) return false;
    while (i->prods.h) delProd(i->prods.h->d);
    for (auto n = grupos.h; n; n = n->s) n->d->integrantes.del([&](string s) { return s == c; });
    invs.del([&](Investigador* x) { return x->ced == c; }); 
    delete i; 
    return true;
}

string deshacerUltimo() {
    Accion a; 
    if (!deshacer.pop(a)) return "Nada que deshacer";
    if (a.tipo == 'A') delProd(a.id);
    else if (a.tipo == 'P' && P(a.id)) P(a.id)->activo = !P(a.id)->activo;
    else if (a.tipo == 'G' && G(a.clave)) G(a.clave)->activo = !G(a.clave)->activo;
    else if (a.tipo == 'I' && I(a.clave)) I(a.clave)->activo = !I(a.clave)->activo;
    return "Accion deshecha";
}

// ---------------------------------------------------------- Persistencia
string L(string s) { for (char& c : s) if (c == '|' || c == '\n') c = '/'; return s; }

vector<string> split(const string& s, char d) { 
    vector<string> v; 
    string x; 
    stringstream ss(s); 
    while (getline(ss, x, d)) v.push_back(x); 
    return v; 
}

void guardar() {
    ofstream f(ARCHIVO);
    for (auto n = grupos.h; n; n = n->s) {
        Grupo* g = n->d; 
        f << "G|" << L(g->cod) << "|" << L(g->nombre) << "|" << L(g->clasif) << "|" << L(g->lider) << "|" << g->activo << "\n";
        for (auto m = g->integrantes.h; m; m = m->s) f << "M|" << L(g->cod) << "|" << L(m->d) << "\n";
        for (auto m = g->plan.h; m; m = m->s) f << "L|" << L(g->cod) << "|" << L(m->d) << "\n";
    }
    for (auto n = invs.h; n; n = n->s) 
        f << "I|" << L(n->d->ced) << "|" << L(n->d->nombre) << "|" << L(n->d->cat) << "|" << n->d->activo << "\n";
    
    for (auto n = prods.h; n; n = n->s) { 
        Producto* p = n->d;
        f << "P|" << p->id << "|" << L(p->titulo) << "|" << L(p->tipo) << "|" << L(p->cat) << "|" << p->anio << "|" << p->validado << "|" << p->activo << "|" << L(p->ced) << "|" << L(p->grupo) << "\n"; 
    }
}

bool cargar() {
    ifstream f(ARCHIVO); 
    if (!f) return false; 
    string ln; 
    vector<vector<string>> miembros;

    while (getline(f, ln)) {
        auto t = split(ln, '|'); 
        if (t.empty()) continue;
        if (t[0] == "G" && t.size() >= 6) { Grupo* g = addGrupo(t[1], t[2], t[3], t[4]); if (g) g->activo = (t[5] == "1"); }
        else if (t[0] == "I" && t.size() >= 5) { Investigador* i = addInv(t[1], t[2], t[3]); i->activo = (t[4] == "1"); }
        else if (t[0] == "M" && t.size() >= 3) miembros.push_back(t);
        else if (t[0] == "L" && t.size() >= 3 && G(t[1])) G(t[1])->plan.add(t[2]);
        else if (t[0] == "P" && t.size() >= 10) { 
            Producto* p = addProd(t[2], t[3], t[4], stoi(t[5]), t[8], t[9], t[6] == "1", stoi(t[1]), false);
            p->activo = (t[7] == "1"); 
            if (!p->validado) pendientes.encolar(p->id); 
        }
    }
    for (auto& m : miembros) addMiembro(m[1], m[2]);
    Accion a; 
    while (deshacer.pop(a)) {}
    return true;
}

int importarCSV(const string& ruta) { 
    ifstream f(ruta); 
    string ln; 
    int n = 0; 
    getline(f, ln); // Leer encabezado
    while (getline(f, ln)) {
        auto t = split(ln, ','); 
        if (t.size() < 7) continue;
        addGrupo(t[0], t[0]); 
        addInv(t[1], t[2]); 
        addMiembro(t[0], t[1]);
        addProd(t[3], t[4], t[5], stoi(t[6]), t[1], t[0], t.size() > 7 && (t[7] == "1" || t[7] == "si")); 
        n++;
    }
    return n;
}

// ---------------------------------------------------------- Estadística
bool pasa(Producto* p, int vista, const string& clave, int ventana) {
    if (!p->activo) return false;
    if (ventana > 0 && p->anio < anioActual() - ventana + 1) return false;
    if (vista == 1 && p->grupo != clave) return false;
    if (vista == 2 && p->ced != clave) return false;
    if (vista == 3 && p->tipo != clave) return false;
    return true;
}

void tablaMapa(const string& titulo, const map<string, int>& m, int total) {
    cout << "\n  " << titulo << "\n  " << string(46, '-') << "\n";
    for (auto& kv : m) { 
        int b = total ? kv.second * 20 / total : 0;
        cout << "  " << left << setw(22) << kv.first.substr(0, 21) << right << setw(5) << kv.second << "  " << string(b, '#') << "\n"; 
    }
}

void estadisticas(int vista, const string& clave, int ventana) {
    map<string, int> anio, tipo, cat, val, gr, inv; 
    int total = 0;

    for (auto n = prods.h; n; n = n->s) { 
        Producto* p = n->d; 
        if (!pasa(p, vista, clave, ventana)) continue;
        total++; 
        anio[to_string(p->anio)]++; 
        tipo[p->tipo]++; 
        cat[p->cat]++; 
        val[p->validado ? "Validados" : "Sin validar"]++; 
        gr[p->grupo]++; 
        inv[p->ced]++; 
    }

    cout << "\n==== RESUMEN PEA-i UPC | vista=" << vista << " clave=" << clave << " ventana=" << (ventana ? to_string(ventana) + " anios" : "todos")
         << " ====\n  Total de productos: " << total << "\n";
    tablaMapa("Productos por anio", anio, total); 
    tablaMapa("Productos por tipo", tipo, total);
    tablaMapa("Productos por categoria", cat, total); 
    tablaMapa("Validacion", val, total);
    tablaMapa("Productos por grupo", gr, total); 
    tablaMapa("Productos por investigador (cedula)", inv, total);

    if (total && !inv.empty()) { 
        double s = 0; 
        for (auto& kv : inv) s += kv.second;
        cout << "\n  Promedio de productos por investigador: " << fixed << setprecision(2) << s / inv.size() << "\n"; 
    }
}

// ---------------------------------------------------------- Interfaz
string ask(const string& m, const string& d = "") { 
    cout << m << (d.empty() ? "" : " [" + d + "]") << ": "; 
    string s; 
    getline(cin, s); 
    return s.empty() ? d : s; 
}

void crudGrupo() { 
    while (true) {
        cout << "\n--- GRUPOS --- 1.Crear 2.Listar 3.Modificar 4.Activar/Desactivar 5.Eliminar 6.Detalle 7.Integrante 8.Plan 0.Volver\n"; 
        string o = ask("Opcion");
        if (o == "0") return;
        if (o == "1") cout << (addGrupo(ask("Codigo"), ask("Nombre"), ask("Clasificacion"), ask("Lider")) ? "OK\n" : "Ya existe\n");
        else if (o == "2") {
            for (auto n = grupos.h; n; n = n->s) 
                cout << "  " << n->d->cod << " | " << n->d->nombre << " | " << n->d->clasif << " | " << n->d->lider << (n->d->activo ? "" : " (DESACTIVADO)") << "\n";
        }
        else { 
            Grupo* g = G(ask("Codigo")); 
            if (!g) { cout << "No encontrado\n"; continue; }
            if (o == "3") { 
                string c = ask("Campo (nombre/clasificacion/lider)"), v = ask("Nuevo valor"); 
                (c == "nombre" ? g->nombre : c == "clasificacion" ? g->clasif : g->lider) = v; 
            }
            else if (o == "4") { g->activo = !g->activo; deshacer.push({'G', 0, g->cod}); cout << (g->activo ? "Activo\n" : "Desactivado\n"); }
            else if (o == "5") cout << (delGrupo(g->cod) ? "Eliminado\n" : "Error\n");
            else if (o == "6") { 
                cout << "  " << g->nombre << " lider " << g->lider << "\n  Integrantes:"; 
                for (auto m = g->integrantes.h; m; m = m->s) cout << " " << m->d;
                cout << "\n  Plan:"; 
                for (auto m = g->plan.h; m; m = m->s) cout << " | " << m->d; 
                cout << "\n  Productos:\n"; 
                for (auto m = g->prods.h; m; m = m->s) if (P(m->d)) cout << "   - " << P(m->d)->titulo << " (" << P(m->d)->anio << ")\n"; 
            }
            else if (o == "7") cout << (addMiembro(g->cod, ask("Cedula")) ? "Agregado\n" : "Error\n");
            else if (o == "8") g->plan.add(ask("Item del plan")); 
        } 
    } 
}

void crudInv() { 
    while (true) {
        cout << "\n--- INVESTIGADORES --- 1.Crear 2.Listar 3.Modificar 4.Activar/Desactivar 5.Eliminar 6.Productos 0.Volver\n"; 
        string o = ask("Opcion");
        if (o == "0") return;
        if (o == "1") { addInv(ask("Cedula"), ask("Nombre"), ask("Categoria")); cout << "OK\n"; }
        else if (o == "2") {
            for (auto n = invs.h; n; n = n->s) 
                cout << "  " << n->d->ced << " | " << n->d->nombre << " | " << n->d->cat << (n->d->activo ? "" : " (DESACTIVADO)") << "\n";
        }
        else { 
            Investigador* i = I(ask("Cedula")); 
            if (!i) { cout << "No encontrado\n"; continue; }
            if (o == "3") { string c = ask("Campo (nombre/categoria)"), v = ask("Nuevo valor"); (c == "nombre" ? i->nombre : i->cat) = v; }
            else if (o == "4") { i->activo = !i->activo; deshacer.push({'I', 0, i->ced}); cout << (i->activo ? "Activo\n" : "Desactivado\n"); }
            else if (o == "5") cout << (delInv(i->ced) ? "Eliminado\n" : "Error\n");
            else if (o == "6") { 
                for (auto m = i->prods.h; m; m = m->s) 
                    if (P(m->d)) cout << "  [" << m->d << "] " << P(m->d)->titulo << " (" << P(m->d)->anio << ")\n"; 
            } 
        } 
    } 
}

void crudProd() { 
    while (true) {
        cout << "\n--- PRODUCTOS --- 1.Crear 2.Listar 3.Modificar 4.Activar/Desactivar 5.Eliminar 0.Volver\n"; 
        string o = ask("Opcion");
        if (o == "0") return;
        if (o == "1") { 
            Producto* p = addProd(ask("Titulo"), ask("Tipo (Articulo/Libro/Software...)"), ask("Categoria (A1,A2,B,C)"), stoi(ask("Anio", to_string(anioActual()))), ask("Cedula investigador"), ask("Codigo grupo"));
            cout << "Producto " << p->id << " creado; en cola de validacion\n"; 
        }
        else if (o == "2") { 
            Lista<Producto*>& l = prods; 
            for (auto n = l.h; n; n = n->s) { 
                Producto* p = n->d;
                cout << "  [" << p->id << "] " << p->titulo << " | " << p->tipo << " | " << p->cat << " | " << p->anio << " | val=" << p->validado << " | " << p->grupo << (p->activo ? "" : " (DESACTIVADO)") << "\n"; 
            } 
        }
        else { 
            string inputId = ask("Id");
            if (inputId.empty()) continue;
            Producto* p = P(stoi(inputId)); 
            if (!p) { cout << "No encontrado\n"; continue; }
            if (o == "3") { 
                string c = ask("Campo (titulo/tipo/categoria/anio/validado)"), v = ask("Nuevo valor");
                if (c == "titulo") p->titulo = v; 
                else if (c == "tipo") p->tipo = v; 
                else if (c == "categoria") p->cat = v; 
                else if (c == "anio") p->anio = stoi(v); 
                else if (c == "validado") p->validado = (v == "1" || v == "si"); 
            }
            else if (o == "4") { p->activo = !p->activo; deshacer.push({'P', p->id, ""}); cout << (p->activo ? "Activo\n" : "Desactivado\n"); }
            else if (o == "5") cout << (delProd(p->id) ? "Eliminado\n" : "Error\n"); 
        } 
    } 
}

void demo() {
    srand(1); 
    addGrupo("COL0001", "Grupo GIDSI", "A", "Ana Perez"); 
    addGrupo("COL0002", "Grupo BioCesar", "B", "Luis Mora");
    const char* nom[] = {"Ana Perez", "Carlos Ruiz", "Luis Mora", "Maria Diaz"}; 
    const char* tp[] = {"Articulo", "Libro", "Software", "Capitulo"}; 
    const char* ct[] = {"A1", "A2", "B", "C"};

    for (int i = 0; i < 4; i++) { 
        addInv(to_string(i + 1), nom[i], "Asociado"); 
        addMiembro(i < 2 ? "COL0001" : "COL0002", to_string(i + 1)); 
    }

    for (int k = 0; k < 60; k++) { 
        int i = rand() % 4; 
        addProd("Producto de ejemplo", tp[rand() % 4], ct[rand() % 4], anioActual() - rand() % 9, to_string(i + 1), i < 2 ? "COL0001" : "COL0002", rand() % 10 > 2); 
    }
    cout << "Demo cargada\n";
}

int main() {
    ifstream t(ARCHIVO); 
    if (t && ask("Cargar datos guardados? (s/n)", "s") == "s") { 
        cargar(); 
        cout << "Datos cargados\n"; 
    }

    while (true) {
        cout << "\nGrupos " << grupos.n << " | Investigadores " << invs.n << " | Productos " << prods.n << " | Pendientes " << pendientes.n << " | Deshacer " << deshacer.n
             << "\n1.Grupos 2.Investigadores 3.Productos 4.Cola de validacion 5.Deshacer 6.Importar CSV 7.Estadisticas 8.Guardar 9.Demo 0.Salir\n";
        string o = ask("Opcion");

        try {
            if (o == "0") { 
                if (ask("Guardar? (s/n)", "s") == "s") guardar(); 
                return 0; 
            }
            else if (o == "1") crudGrupo(); 
            else if (o == "2") crudInv(); 
            else if (o == "3") crudProd();
            else if (o == "4") { 
                if (!pendientes.h) { cout << "Cola vacia\n"; continue; } 
                Producto* p = P(pendientes.h->d); 
                int id; 
                pendientes.desencolar(id);
                if (p) { 
                    cout << "Siguiente: [" << p->id << "] " << p->titulo << "\n"; 
                    p->validado = (ask("Aprobar? (s/n)", "s") == "s"); 
                } 
            }
            else if (o == "5") cout << deshacerUltimo() << "\n";
            else if (o == "6") cout << importarCSV(ask("Ruta CSV")) << " productos importados\n";
            else if (o == "7") { 
                int v = stoi(ask("Vista 0.Todo 1.Grupo 2.Investigador 3.Tipo producto", "0")); 
                string k = v ? ask("Llave (codigo/cedula/tipo)") : "";
                int w = stoi(ask("Ventana en anios (0=todos)", "0")); 
                estadisticas(v, k, w); 
            }
            else if (o == "8") { guardar(); cout << "Guardado\n"; }
            else if (o == "9") demo();
        } catch (const exception& e) { 
            cout << "Entrada invalida\n"; 
        }

        if (!cin) return 0;
    }
}