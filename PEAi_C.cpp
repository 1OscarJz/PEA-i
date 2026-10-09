// =====================================================================
// PEA-i - Programa Estadístico de Análisis de Investigación  (versión C++)
// Universidad Popular del Cesar - Ingeniería de Sistemas - Estructura de Datos (Taller 2)
//
// PROGRAMACIÓN ESTRUCTURADA: solo struct y funciones (sin clases ni métodos).
//
// FLUJO DE TRABAJO (interoperabilidad Python <-> C++):
//   1. El programa en PYTHON hace el scraping de SCIENTI (GrupLAC / CvLAC) y, con
//      Archivo > "Exportar para C++ (.txt)", genera el archivo  pea_i_datos_cpp.txt
//   2. Este programa en C++ carga ese archivo (formato PEA-i-TXT v1), permite el CRUD
//      completo, muestra las estadísticas en tablas y vuelve a guardar el mismo formato
//      (Python lo puede abrir con Archivo > "Abrir archivo .txt (de C++)").
//   3. Desde el menú "Importar datos" de ESTE programa se puede pegar una URL o elegir
//      un archivo HTML/PDF/CSV: C++ guarda sus datos, llama a Python en modo consola
//      (python Taller2_PEAi.py --cli ...), Python hace el scraping y escribe el resultado,
//      y C++ recarga los datos. Requiere Python y Taller2_PEAi.py en la misma carpeta.
//
// FORMATO PEA-i-TXT v1 (UTF-8, campos separados por |, booleanos 1/0, autores con ;)
//   C|contador_prod|contador_inv
//   G|codigo|nombre|lider|categoria|url|activo
//   I|id|nombre|cod_rh|email|formacion|categoria|activo
//   M|cod_grupo|id_investigador|vinculacion|horas|periodo|activo
//   P|id|titulo|tipo|categoria|anio|validado|cod_grupo|ids_autores|activo
//   Q|tipo|origen|estado|modo|codigo
//   FIN|n_grupos|n_investigadores|n_integrantes|n_productos
//
// ESTRUCTURAS DE DATOS (implementadas con punteros, sin STL):
//   LISTA enlazada ........ grupos, investigadores, productos, integrantes
//   MULTILISTA ............ un mismo Producto* vive en la lista maestra, la de su grupo,
//                           la de cada autor y en una celda del hipercubo
//   PILA .................. historial de operaciones (deshacer)
//   COLA .................. importaciones pendientes (FIFO)
//   HIPERCUBO ............. celdas (grupo, investigador, tipo, categoria, anio)
// (std::string, std::vector, std::map y std::set se usan solo como apoyo para texto y
//  para devolver resultados de consultas; no almacenan las estructuras del modelo.)
//
// COMPILAR:   g++ -O2 -o pea Taller2_PEAi.cpp                   (Linux / MinGW / Dev-C++)
//             Compatible con C++98 en adelante (no usa to_string ni lambdas).
//             Visual Studio: cl /EHsc /utf-8 Taller2_PEAi.cpp
// =====================================================================
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif
using namespace std;

// Conversión número -> texto propia (std::to_string no existe en MinGW antiguos).
string aTexto(long valor) {
    ostringstream o;
    o << valor;
    return o.str();
}

string idConPrefijo(const char* prefijo, int numero) {
    ostringstream o;
    o << prefijo << setw(4) << setfill('0') << numero;
    return o.str();
}

// =====================================================================
// 1. NODO, LISTA, PILA Y COLA (genéricas con void*)
// =====================================================================
struct Nodo {
    void* dato;
    Nodo* sig;
};

struct Lista {
    Nodo* cabeza;
    Nodo* cola;
    int tam;
};

struct Pila {
    Nodo* tope;
    int tam;
};

struct Cola {
    Nodo* frente;
    Nodo* final;
    int tam;
};

typedef bool (*Criterio)(void* dato, const string& valor);

Lista listaCrear() {
    Lista l;
    l.cabeza = NULL;
    l.cola = NULL;
    l.tam = 0;
    return l;
}

void listaInsertarFinal(Lista& l, void* d) {
    Nodo* n = new Nodo;
    n->dato = d;
    n->sig = NULL;
    if (l.cabeza == NULL) l.cabeza = n;
    else l.cola->sig = n;
    l.cola = n;
    l.tam++;
}

void* listaBuscar(const Lista& l, Criterio c, const string& valor) {
    for (Nodo* n = l.cabeza; n != NULL; n = n->sig)
        if (c(n->dato, valor)) return n->dato;
    return NULL;
}

// Elimina el nodo que apunta a 'd' (identidad de puntero). No libera el dato.
bool listaEliminar(Lista& l, void* d) {
    Nodo* ant = NULL;
    Nodo* act = l.cabeza;
    while (act != NULL) {
        if (act->dato == d) {
            if (ant == NULL) l.cabeza = act->sig;
            else ant->sig = act->sig;
            if (act == l.cola) l.cola = ant;
            delete act;
            l.tam--;
            return true;
        }
        ant = act;
        act = act->sig;
    }
    return false;
}

void listaLiberarNodos(Lista& l) {
    Nodo* n = l.cabeza;
    while (n != NULL) {
        Nodo* sig = n->sig;
        delete n;
        n = sig;
    }
    l = listaCrear();
}

Pila pilaCrear() {
    Pila p;
    p.tope = NULL;
    p.tam = 0;
    return p;
}

bool pilaVacia(const Pila& p) { return p.tope == NULL; }

void pilaApilar(Pila& p, void* d) {
    Nodo* n = new Nodo;
    n->dato = d;
    n->sig = p.tope;
    p.tope = n;
    p.tam++;
}

void* pilaDesapilar(Pila& p) {
    if (pilaVacia(p)) return NULL;
    Nodo* n = p.tope;
    void* d = n->dato;
    p.tope = n->sig;
    delete n;
    p.tam--;
    return d;
}

Cola colaCrear() {
    Cola c;
    c.frente = NULL;
    c.final = NULL;
    c.tam = 0;
    return c;
}

bool colaVacia(const Cola& c) { return c.frente == NULL; }

void colaEncolar(Cola& c, void* d) {
    Nodo* n = new Nodo;
    n->dato = d;
    n->sig = NULL;
    if (colaVacia(c)) c.frente = n;
    else c.final->sig = n;
    c.final = n;
    c.tam++;
}

void* colaDesencolar(Cola& c) {
    if (colaVacia(c)) return NULL;
    Nodo* n = c.frente;
    void* d = n->dato;
    c.frente = n->sig;
    if (c.frente == NULL) c.final = NULL;
    delete n;
    c.tam--;
    return d;
}

// =====================================================================
// 2. REGISTROS DEL MODELO
// =====================================================================
struct Integrante {
    string idInv, vinculacion, horas, periodo;
    bool activo;
};

struct Grupo {
    string codigo, nombre, lider, categoria, url;
    bool activo;
    Lista integrantes;   // sublista de Integrante*
    Lista productos;     // sublista de Producto*   (multilista)
};

struct Investigador {
    string id, nombre, codRh, email, formacion, categoria;
    bool activo;
    Lista productos;     // sublista de Producto*   (multilista)
};

struct Producto {
    string id, titulo, tipo, categoria;
    int anio;
    bool validado;
    string grupo;                 // código del grupo
    vector<string> autores;       // ids de investigadores
    bool activo;
};

struct Importacion {
    string tipo, origen, estado, modo, codigo;
};

// Operación del historial (PILA). Guarda "instantáneas" en el mismo formato de texto.
struct Operacion {
    string op, ent, clave;           // op: crear | modificar | desactivar | eliminar
    vector<string> lineas;           // registro(s) antes del cambio (G+M..., I, P)
    vector<string> productos;        // productos eliminados en cascada
    bool antesActivo;
};

// =====================================================================
// 3. HIPERCUBO  (grupo, investigador, tipo, categoria, anio)
// =====================================================================
struct Celda {
    string grupo, inv, tipo, categoria;
    int anio;
    Lista productos;
    Celda* sig;
};

struct Hipercubo {
    Celda* cabeza;
    int nCeldas;
};

struct Filtros {
    string grupo, inv, tipo, categoria;   // vacío = sin filtro
    int anio, anioDesde, anioHasta;       // 0 = sin filtro
    bool soloValidados, soloActivos;
};

struct Sistema {
    Lista grupos, investigadores, productos;
    Hipercubo cubo;
    Pila historial;
    Cola importaciones;
    int contProd, contInv;
};

// Estado global del programa
Sistema S;
int VENTANA_N = 0;                       // 0 = histórico completo
string RUTA_DATOS = "pea_i_datos_cpp.txt";
#ifdef _WIN32
string CMD_PYTHON = "python";
#else
string CMD_PYTHON = "python3";
#endif
string SCRIPT_PY = "Taller2_PEAi.py";                         // script de Python (misma carpeta)
const string ARCHIVO_INTERCAMBIO = "pea_i_intercambio.tmp.txt";
bool PYTHON_VERIFICADO = false;                              // ya se comprobó que el comando funciona
bool SUCIO = false;

Filtros filtrosNuevos() {
    Filtros f;
    f.anio = 0;
    f.anioDesde = 0;
    f.anioHasta = 0;
    f.soloValidados = false;
    f.soloActivos = true;
    return f;
}

int anioActual() {
    time_t t = time(NULL);
    struct tm* lt = localtime(&t);
    return lt->tm_year + 1900;
}

void aplicarVentana(Filtros& f) {
    if (VENTANA_N > 0) {
        f.anioHasta = anioActual();
        f.anioDesde = f.anioHasta - VENTANA_N + 1;
    }
}

vector<string> autoresONd(const Producto* p) {
    if (p->autores.empty()) return vector<string>(1, "N/D");
    return p->autores;
}

Celda* cuboBuscarCelda(const Hipercubo& c, const string& g, const string& i,
                       const string& t, const string& cat, int anio) {
    for (Celda* x = c.cabeza; x != NULL; x = x->sig)
        if (x->anio == anio && x->grupo == g && x->inv == i && x->tipo == t &&
            x->categoria == cat)
            return x;
    return NULL;
}

void cuboPoner(Hipercubo& c, Producto* p) {
    vector<string> aut = autoresONd(p);
    for (size_t k = 0; k < aut.size(); k++) {
        Celda* x = cuboBuscarCelda(c, p->grupo, aut[k], p->tipo, p->categoria, p->anio);
        if (x == NULL) {
            x = new Celda;
            x->grupo = p->grupo;
            x->inv = aut[k];
            x->tipo = p->tipo;
            x->categoria = p->categoria;
            x->anio = p->anio;
            x->productos = listaCrear();
            x->sig = c.cabeza;
            c.cabeza = x;
            c.nCeldas++;
        }
        listaInsertarFinal(x->productos, p);
    }
}

// Debe llamarse ANTES de cambiar los campos del producto.
void cuboQuitar(Hipercubo& c, Producto* p) {
    vector<string> aut = autoresONd(p);
    for (size_t k = 0; k < aut.size(); k++) {
        Celda* ant = NULL;
        Celda* x = c.cabeza;
        while (x != NULL) {
            if (x->anio == p->anio && x->grupo == p->grupo && x->inv == aut[k] &&
                x->tipo == p->tipo && x->categoria == p->categoria) {
                listaEliminar(x->productos, p);
                if (x->productos.tam == 0) {
                    if (ant == NULL) c.cabeza = x->sig;
                    else ant->sig = x->sig;
                    delete x;
                    c.nCeldas--;
                }
                break;
            }
            ant = x;
            x = x->sig;
        }
    }
}

bool coordenadaPasa(const Celda* x, const Filtros& f) {
    if (!f.grupo.empty() && x->grupo != f.grupo) return false;
    if (!f.inv.empty() && x->inv != f.inv) return false;
    if (!f.tipo.empty() && x->tipo != f.tipo) return false;
    if (!f.categoria.empty() && x->categoria != f.categoria) return false;
    if (f.anio != 0 && x->anio != f.anio) return false;
    if (f.anioDesde != 0 && x->anio < f.anioDesde) return false;
    if (f.anioHasta != 0 && x->anio > f.anioHasta) return false;
    return true;
}

bool productoPasa(const Producto* p, const Filtros& f) {
    if (f.soloActivos && !p->activo) return false;
    if (f.soloValidados && !p->validado) return false;
    return true;
}

// Rebanada del cubo: productos distintos que cumplen los filtros.
vector<Producto*> cuboConsultar(const Hipercubo& c, const Filtros& f) {
    vector<Producto*> r;
    set<string> vistos;
    for (Celda* x = c.cabeza; x != NULL; x = x->sig) {
        if (!coordenadaPasa(x, f)) continue;
        for (Nodo* n = x->productos.cabeza; n != NULL; n = n->sig) {
            Producto* p = (Producto*)n->dato;
            if (productoPasa(p, f) && vistos.insert(p->id).second) r.push_back(p);
        }
    }
    return r;
}

// Agregación (roll-up) por una dimensión: valor -> cantidad de productos distintos.
// dim: "grupo" | "inv" | "tipo" | "categoria" | "anio"
map<string, int> cuboResumen(const Hipercubo& c, const string& dim, const Filtros& f) {
    map<string, set<string> > conj;
    for (Celda* x = c.cabeza; x != NULL; x = x->sig) {
        if (!coordenadaPasa(x, f)) continue;
        string valor;
        if (dim == "grupo") valor = x->grupo;
        else if (dim == "inv") valor = x->inv;
        else if (dim == "tipo") valor = x->tipo;
        else if (dim == "categoria") valor = x->categoria;
        else valor = aTexto(x->anio);
        for (Nodo* n = x->productos.cabeza; n != NULL; n = n->sig) {
            Producto* p = (Producto*)n->dato;
            if (productoPasa(p, f)) conj[valor].insert(p->id);
        }
    }
    map<string, int> r;
    for (map<string, set<string> >::iterator it = conj.begin(); it != conj.end(); ++it)
        r[it->first] = (int)it->second.size();
    return r;
}

// =====================================================================
// 4. UTILIDADES DE TEXTO Y ENTRADA/SALIDA
// =====================================================================
string quitarSep(string s) {
    for (size_t i = 0; i < s.size(); i++) {
        if (s[i] == '|') s[i] = '/';
        else if (s[i] == '\n' || s[i] == '\r') s[i] = ' ';
    }
    return s;
}

vector<string> dividir(const string& s, char sep) {
    vector<string> r;
    string cur;
    for (size_t i = 0; i < s.size(); i++) {
        if (s[i] == sep) {
            r.push_back(cur);
            cur.clear();
        } else {
            cur += s[i];
        }
    }
    r.push_back(cur);
    return r;
}

string unir(const vector<string>& v, const string& sep) {
    string r;
    for (size_t i = 0; i < v.size(); i++) {
        if (i > 0) r += sep;
        r += v[i];
    }
    return r;
}

string recortarEspacios(const string& s) {
    size_t a = 0, b = s.size();
    while (a < b && (s[a] == ' ' || s[a] == '\t' || s[a] == '\r' || s[a] == '\n')) a++;
    while (b > a && (s[b - 1] == ' ' || s[b - 1] == '\t' || s[b - 1] == '\r' || s[b - 1] == '\n')) b--;
    return s.substr(a, b - a);
}

string minusculas(string s) {
    for (size_t i = 0; i < s.size(); i++)
        if (s[i] >= 'A' && s[i] <= 'Z') s[i] = (char)(s[i] - 'A' + 'a');
    return s;
}

bool contiene(const string& texto, const string& buscado) {
    if (buscado.empty()) return true;
    return minusculas(texto).find(minusculas(buscado)) != string::npos;
}

int anchoUtf8(const string& s) {
    int n = 0;
    for (size_t i = 0; i < s.size(); i++)
        if ((s[i] & 0xC0) != 0x80) n++;
    return n;
}

string cortar(const string& s, int limite) {
    if (anchoUtf8(s) <= limite) return s;
    string r;
    int n = 0;
    for (size_t i = 0; i < s.size(); i++) {
        if ((s[i] & 0xC0) != 0x80) {
            if (n == limite - 1) break;
            n++;
        }
        r += s[i];
    }
    return r + "…";
}

string pad(const string& s, int ancho) {
    string r = cortar(s, ancho - 1);          // deja siempre un espacio entre columnas
    int faltan = ancho - anchoUtf8(r);
    if (faltan > 0) r += string(faltan, ' ');
    return r;
}

string padIzq(const string& s, int ancho) {
    int faltan = ancho - anchoUtf8(s);
    return (faltan > 0 ? string(faltan, ' ') : string("")) + s;
}

string leerLinea(const string& mensaje) {
    cout << mensaje;
    string s;
    if (!getline(cin, s)) {
        cout << "\n(Fin de la entrada)\n";
        exit(0);
    }
    return recortarEspacios(s);
}

// Campo de edición: Enter conserva el valor actual.
string leerCampo(const string& mensaje, const string& actual) {
    string s = leerLinea(mensaje + " [" + actual + "]: ");
    return s.empty() ? actual : s;
}

int leerEntero(const string& mensaje, int minimo, int maximo) {
    while (true) {
        string s = leerLinea(mensaje);
        char* fin = NULL;
        long v = strtol(s.c_str(), &fin, 10);
        if (!s.empty() && *fin == '\0' && v >= minimo && v <= maximo) return (int)v;
        cout << "  Valor inválido: escriba un número entre " << minimo << " y " << maximo << ".\n";
    }
}

bool confirmar(const string& mensaje) {
    string s = leerLinea(mensaje + " (s/n): ");
    return !s.empty() && (s[0] == 's' || s[0] == 'S');
}

void esperarEnter() { leerLinea("\n[Enter para continuar] "); }

void titulo(const string& texto) {
    cout << "\n==================================================================\n";
    cout << "  " << texto << "\n";
    cout << "==================================================================\n";
}

string siNo(bool b) { return b ? "Sí" : "No"; }

// =====================================================================
// 5. BÚSQUEDAS Y ARREGLOS AUXILIARES
// =====================================================================
bool critGrupo(void* d, const string& v) { return ((Grupo*)d)->codigo == v; }
bool critInv(void* d, const string& v) { return ((Investigador*)d)->id == v; }
bool critProd(void* d, const string& v) { return ((Producto*)d)->id == v; }
bool critInteg(void* d, const string& v) { return ((Integrante*)d)->idInv == v; }

Grupo* buscarGrupo(Sistema& s, const string& c) { return (Grupo*)listaBuscar(s.grupos, critGrupo, c); }
Investigador* buscarInv(Sistema& s, const string& i) { return (Investigador*)listaBuscar(s.investigadores, critInv, i); }
Producto* buscarProd(Sistema& s, const string& i) { return (Producto*)listaBuscar(s.productos, critProd, i); }
Integrante* buscarInteg(Grupo* g, const string& i) { return (Integrante*)listaBuscar(g->integrantes, critInteg, i); }

vector<Grupo*> arregloGrupos(const Lista& l, bool soloActivos) {
    vector<Grupo*> r;
    for (Nodo* n = l.cabeza; n != NULL; n = n->sig) {
        Grupo* g = (Grupo*)n->dato;
        if (!soloActivos || g->activo) r.push_back(g);
    }
    return r;
}

vector<Investigador*> arregloInv(const Lista& l, bool soloActivos) {
    vector<Investigador*> r;
    for (Nodo* n = l.cabeza; n != NULL; n = n->sig) {
        Investigador* i = (Investigador*)n->dato;
        if (!soloActivos || i->activo) r.push_back(i);
    }
    return r;
}

vector<Producto*> arregloProd(const Lista& l) {
    vector<Producto*> r;
    for (Nodo* n = l.cabeza; n != NULL; n = n->sig) r.push_back((Producto*)n->dato);
    return r;
}

vector<Integrante*> arregloInteg(const Lista& l) {
    vector<Integrante*> r;
    for (Nodo* n = l.cabeza; n != NULL; n = n->sig) r.push_back((Integrante*)n->dato);
    return r;
}

bool menorProductoId(Producto* a, Producto* b) { return a->id < b->id; }

bool mayorCuenta(const pair<string, int>& a, const pair<string, int>& b) {
    return a.second != b.second ? a.second > b.second : a.first < b.first;
}

string nombreInv(Sistema& s, const string& id) {
    Investigador* i = buscarInv(s, id);
    return i != NULL ? i->nombre : id;
}

// =====================================================================
// 6. SERIALIZACIÓN (mismo formato del archivo y de las instantáneas del historial)
// =====================================================================
string bit(bool b) { return b ? "1" : "0"; }

string lineaG(Grupo* g) {
    return "G|" + quitarSep(g->codigo) + "|" + quitarSep(g->nombre) + "|" + quitarSep(g->lider) +
           "|" + quitarSep(g->categoria) + "|" + quitarSep(g->url) + "|" + bit(g->activo);
}

string lineaI(Investigador* i) {
    return "I|" + quitarSep(i->id) + "|" + quitarSep(i->nombre) + "|" + quitarSep(i->codRh) +
           "|" + quitarSep(i->email) + "|" + quitarSep(i->formacion) + "|" +
           quitarSep(i->categoria) + "|" + bit(i->activo);
}

string lineaM(const string& codGrupo, Integrante* m) {
    return "M|" + quitarSep(codGrupo) + "|" + quitarSep(m->idInv) + "|" +
           quitarSep(m->vinculacion) + "|" + quitarSep(m->horas) + "|" +
           quitarSep(m->periodo) + "|" + bit(m->activo);
}

string lineaP(Producto* p) {
    return "P|" + quitarSep(p->id) + "|" + quitarSep(p->titulo) + "|" + quitarSep(p->tipo) +
           "|" + quitarSep(p->categoria) + "|" + aTexto(p->anio) + "|" + bit(p->validado) +
           "|" + quitarSep(p->grupo) + "|" + unir(p->autores, ";") + "|" + bit(p->activo);
}

// Construye un Producto (valor, no puntero) desde los campos de una línea P.
bool productoDesdeCampos(const vector<string>& c, Producto& p) {
    if (c.size() < 10) return false;
    p.id = c[1];
    p.titulo = c[2];
    p.tipo = c[3];
    p.categoria = c[4];
    p.anio = atoi(c[5].c_str());
    p.validado = (c[6] == "1");
    p.grupo = c[7];
    p.autores.clear();
    vector<string> aut = dividir(c[8], ';');
    for (size_t i = 0; i < aut.size(); i++)
        if (!aut[i].empty()) p.autores.push_back(aut[i]);
    p.activo = (c[9] == "1");
    return true;
}

// =====================================================================
// 7. NÚCLEO DEL SISTEMA: creación, enlace y limpieza
// =====================================================================
void sistemaIniciar(Sistema& s) {
    s.grupos = listaCrear();
    s.investigadores = listaCrear();
    s.productos = listaCrear();
    s.cubo.cabeza = NULL;
    s.cubo.nCeldas = 0;
    s.historial = pilaCrear();
    s.importaciones = colaCrear();
    s.contProd = 0;
    s.contInv = 0;
}

void sistemaVaciar(Sistema& s) {
    for (Nodo* n = s.productos.cabeza; n != NULL; n = n->sig) delete (Producto*)n->dato;
    listaLiberarNodos(s.productos);
    for (Nodo* n = s.grupos.cabeza; n != NULL; n = n->sig) {
        Grupo* g = (Grupo*)n->dato;
        for (Nodo* m = g->integrantes.cabeza; m != NULL; m = m->sig) delete (Integrante*)m->dato;
        listaLiberarNodos(g->integrantes);
        listaLiberarNodos(g->productos);
        delete g;
    }
    listaLiberarNodos(s.grupos);
    for (Nodo* n = s.investigadores.cabeza; n != NULL; n = n->sig) {
        Investigador* i = (Investigador*)n->dato;
        listaLiberarNodos(i->productos);
        delete i;
    }
    listaLiberarNodos(s.investigadores);
    Celda* x = s.cubo.cabeza;
    while (x != NULL) {
        Celda* sig = x->sig;
        listaLiberarNodos(x->productos);
        delete x;
        x = sig;
    }
    while (!pilaVacia(s.historial)) delete (Operacion*)pilaDesapilar(s.historial);
    while (!colaVacia(s.importaciones)) delete (Importacion*)colaDesencolar(s.importaciones);
    sistemaIniciar(s);
}

Grupo* grupoNuevo(const string& codigo, const string& nombre, const string& lider,
                  const string& categoria, const string& url, bool activo) {
    Grupo* g = new Grupo;
    g->codigo = codigo;
    g->nombre = nombre;
    g->lider = lider;
    g->categoria = categoria;
    g->url = url;
    g->activo = activo;
    g->integrantes = listaCrear();
    g->productos = listaCrear();
    return g;
}

Investigador* investigadorNuevo(const string& id, const string& nombre, const string& codRh,
                                const string& email, const string& formacion,
                                const string& categoria, bool activo) {
    Investigador* i = new Investigador;
    i->id = id;
    i->nombre = nombre;
    i->codRh = codRh;
    i->email = email;
    i->formacion = formacion;
    i->categoria = categoria;
    i->activo = activo;
    i->productos = listaCrear();
    return i;
}

void apilarOperacion(Sistema& s, const Operacion& op) {
    pilaApilar(s.historial, new Operacion(op));
}

string validarProducto(Sistema& s, const string& grupo, const vector<string>& autores, int anio) {
    if (buscarGrupo(s, grupo) == NULL) return "El grupo " + grupo + " no existe";
    for (size_t k = 0; k < autores.size(); k++)
        if (buscarInv(s, autores[k]) == NULL) return "El investigador " + autores[k] + " no existe";
    if (anio < 1900 || anio > anioActual() + 1) return "El año no es válido";
    return "";
}

// Inserta el MISMO registro en la lista del grupo, en la de cada autor y en el hipercubo.
void productoEnlazar(Sistema& s, Producto* p) {
    Grupo* g = buscarGrupo(s, p->grupo);
    if (g != NULL) listaInsertarFinal(g->productos, p);
    for (size_t k = 0; k < p->autores.size(); k++) {
        Investigador* i = buscarInv(s, p->autores[k]);
        if (i != NULL) listaInsertarFinal(i->productos, p);
    }
    cuboPoner(s.cubo, p);
}

void productoDesenlazar(Sistema& s, Producto* p) {
    Grupo* g = buscarGrupo(s, p->grupo);
    if (g != NULL) listaEliminar(g->productos, p);
    for (size_t k = 0; k < p->autores.size(); k++) {
        Investigador* i = buscarInv(s, p->autores[k]);
        if (i != NULL) listaEliminar(i->productos, p);
    }
    cuboQuitar(s.cubo, p);
}

Producto* productoInsertar(Sistema& s, const Producto& datos) {
    Producto* p = new Producto(datos);
    listaInsertarFinal(s.productos, p);
    productoEnlazar(s, p);
    return p;
}

// =====================================================================
// 8. CRUD DE GRUPOS (devuelven "" si todo salió bien o el mensaje de error)
// =====================================================================
string grupoCrear(Sistema& s, const string& codigo, const string& nombre, const string& lider,
                  const string& categoria, const string& url, bool registrar) {
    if (buscarGrupo(s, codigo) != NULL) return "Ya existe un grupo con ese código";
    listaInsertarFinal(s.grupos, grupoNuevo(codigo, nombre, lider, categoria, url, true));
    if (registrar) {
        Operacion op;
        op.op = "crear"; op.ent = "grupo"; op.clave = codigo; op.antesActivo = false;
        apilarOperacion(s, op);
    }
    return "";
}

string grupoModificar(Sistema& s, Grupo* g, const string& nombre, const string& lider,
                      const string& categoria, const string& url, bool registrar) {
    if (registrar) {
        Operacion op;
        op.op = "modificar"; op.ent = "grupo"; op.clave = g->codigo; op.antesActivo = false;
        op.lineas.push_back(lineaG(g));
        apilarOperacion(s, op);
    }
    g->nombre = nombre;
    g->lider = lider;
    g->categoria = categoria;
    g->url = url;
    return "";
}

string grupoDesactivar(Sistema& s, Grupo* g, bool activo, bool registrar) {
    if (registrar) {
        Operacion op;
        op.op = "desactivar"; op.ent = "grupo"; op.clave = g->codigo; op.antesActivo = g->activo;
        apilarOperacion(s, op);
    }
    g->activo = activo;
    return "";
}

Operacion operacionEliminarGrupo(Grupo* g) {
    Operacion op;
    op.op = "eliminar"; op.ent = "grupo"; op.clave = g->codigo; op.antesActivo = false;
    op.lineas.push_back(lineaG(g));
    for (Nodo* n = g->integrantes.cabeza; n != NULL; n = n->sig)
        op.lineas.push_back(lineaM(g->codigo, (Integrante*)n->dato));
    return op;
}

void grupoQuitar(Sistema& s, Grupo* g) {
    for (Nodo* n = g->integrantes.cabeza; n != NULL; n = n->sig) delete (Integrante*)n->dato;
    listaLiberarNodos(g->integrantes);
    listaLiberarNodos(g->productos);
    listaEliminar(s.grupos, g);
    delete g;
}

string grupoEliminar(Sistema& s, Grupo* g, bool registrar) {
    if (g->productos.tam > 0)
        return "El grupo tiene productos: elimínelos, desactive el grupo o use la eliminación en cascada";
    Operacion op = operacionEliminarGrupo(g);
    grupoQuitar(s, g);
    if (registrar) apilarOperacion(s, op);
    return "";
}

string productoEliminar(Sistema& s, Producto* p, bool registrar);

// Elimina el grupo y todos sus productos con UNA sola entrada en el historial.
string grupoEliminarCascada(Sistema& s, Grupo* g) {
    Operacion op = operacionEliminarGrupo(g);
    vector<Producto*> ps = arregloProd(g->productos);
    for (size_t k = 0; k < ps.size(); k++) op.productos.push_back(lineaP(ps[k]));
    for (size_t k = 0; k < ps.size(); k++) productoEliminar(s, ps[k], false);
    grupoQuitar(s, g);
    apilarOperacion(s, op);
    return "";
}

// ---- Integrantes (sublista del grupo) ----
string integranteAgregar(Sistema& s, Grupo* g, const string& idInv, const string& vinc,
                         const string& horas, const string& periodo) {
    if (buscarInv(s, idInv) == NULL) return "El investigador no existe";
    if (buscarInteg(g, idInv) != NULL) return "El investigador ya es integrante de este grupo";
    Integrante* m = new Integrante;
    m->idInv = idInv; m->vinculacion = vinc; m->horas = horas; m->periodo = periodo;
    m->activo = true;
    listaInsertarFinal(g->integrantes, m);
    return "";
}

string integranteEliminar(Grupo* g, const string& idInv) {
    Integrante* m = buscarInteg(g, idInv);
    if (m == NULL) return "El integrante no existe en el grupo";
    listaEliminar(g->integrantes, m);
    delete m;
    return "";
}

// =====================================================================
// 9. CRUD DE INVESTIGADORES
// =====================================================================
bool esIntegranteDeAlgunGrupo(Sistema& s, const string& id) {
    for (Nodo* n = s.grupos.cabeza; n != NULL; n = n->sig)
        if (buscarInteg((Grupo*)n->dato, id) != NULL) return true;
    return false;
}

string investigadorCrear(Sistema& s, const string& nombre, const string& codRh,
                         const string& email, const string& formacion,
                         const string& categoria, bool registrar) {
    s.contInv++;
    string id = idConPrefijo("INV-", s.contInv);
    listaInsertarFinal(s.investigadores,
                       investigadorNuevo(id, nombre, codRh, email, formacion, categoria, true));
    if (registrar) {
        Operacion op;
        op.op = "crear"; op.ent = "investigador"; op.clave = id; op.antesActivo = false;
        apilarOperacion(s, op);
    }
    return "";
}

string investigadorModificar(Sistema& s, Investigador* i, const string& nombre,
                             const string& codRh, const string& email,
                             const string& formacion, const string& categoria, bool registrar) {
    if (registrar) {
        Operacion op;
        op.op = "modificar"; op.ent = "investigador"; op.clave = i->id; op.antesActivo = false;
        op.lineas.push_back(lineaI(i));
        apilarOperacion(s, op);
    }
    i->nombre = nombre; i->codRh = codRh; i->email = email;
    i->formacion = formacion; i->categoria = categoria;
    return "";
}

string investigadorDesactivar(Sistema& s, Investigador* i, bool activo, bool registrar) {
    if (registrar) {
        Operacion op;
        op.op = "desactivar"; op.ent = "investigador"; op.clave = i->id; op.antesActivo = i->activo;
        apilarOperacion(s, op);
    }
    i->activo = activo;
    return "";
}

string investigadorEliminar(Sistema& s, Investigador* i, bool registrar) {
    if (i->productos.tam > 0) return "El investigador tiene productos: desactívelo o elimine sus productos";
    if (esIntegranteDeAlgunGrupo(s, i->id)) return "El investigador es integrante de un grupo: retírelo primero";
    Operacion op;
    op.op = "eliminar"; op.ent = "investigador"; op.clave = i->id; op.antesActivo = false;
    op.lineas.push_back(lineaI(i));
    listaLiberarNodos(i->productos);
    listaEliminar(s.investigadores, i);
    delete i;
    if (registrar) apilarOperacion(s, op);
    return "";
}

// =====================================================================
// 10. CRUD DE PRODUCTOS (multilista + hipercubo)
// =====================================================================
string productoCrear(Sistema& s, const string& grupo, const string& titulo, const string& tipo,
                     int anio, const string& categoria, bool validado,
                     const vector<string>& autores, bool registrar) {
    string error = validarProducto(s, grupo, autores, anio);
    if (!error.empty()) return error;
    s.contProd++;
    string id = idConPrefijo("PRD-", s.contProd);
    Producto p;
    p.id = id; p.titulo = titulo; p.tipo = tipo; p.categoria = categoria; p.anio = anio;
    p.validado = validado; p.grupo = grupo; p.autores = autores; p.activo = true;
    productoInsertar(s, p);
    if (registrar) {
        Operacion op;
        op.op = "crear"; op.ent = "producto"; op.clave = id; op.antesActivo = false;
        apilarOperacion(s, op);
    }
    return "";
}

// 'nuevo' trae los valores a aplicar (titulo, tipo, categoria, anio, validado, grupo, autores).
string productoModificar(Sistema& s, Producto* p, const Producto& nuevo, bool registrar) {
    string error = validarProducto(s, nuevo.grupo, nuevo.autores, nuevo.anio);
    if (!error.empty()) return error;
    if (registrar) {
        Operacion op;
        op.op = "modificar"; op.ent = "producto"; op.clave = p->id; op.antesActivo = false;
        op.lineas.push_back(lineaP(p));
        apilarOperacion(s, op);
    }
    productoDesenlazar(s, p);          // usa las coordenadas ANTIGUAS
    p->titulo = nuevo.titulo; p->tipo = nuevo.tipo; p->categoria = nuevo.categoria;
    p->anio = nuevo.anio; p->validado = nuevo.validado; p->grupo = nuevo.grupo;
    p->autores = nuevo.autores;
    productoEnlazar(s, p);             // usa las coordenadas NUEVAS
    return "";
}

string productoDesactivar(Sistema& s, Producto* p, bool activo, bool registrar) {
    if (registrar) {
        Operacion op;
        op.op = "desactivar"; op.ent = "producto"; op.clave = p->id; op.antesActivo = p->activo;
        apilarOperacion(s, op);
    }
    p->activo = activo;
    return "";
}

string productoEliminar(Sistema& s, Producto* p, bool registrar) {
    Operacion op;
    op.op = "eliminar"; op.ent = "producto"; op.clave = p->id; op.antesActivo = false;
    op.lineas.push_back(lineaP(p));
    productoDesenlazar(s, p);
    listaEliminar(s.productos, p);
    delete p;
    if (registrar) apilarOperacion(s, op);
    return "";
}

// =====================================================================
// 11. DESHACER (usa la PILA de historial)
// =====================================================================
string eliminarEntidad(Sistema& s, const string& ent, const string& clave) {
    if (ent == "grupo") {
        Grupo* g = buscarGrupo(s, clave);
        return g ? grupoEliminar(s, g, false) : "El grupo ya no existe";
    }
    if (ent == "investigador") {
        Investigador* i = buscarInv(s, clave);
        return i ? investigadorEliminar(s, i, false) : "El investigador ya no existe";
    }
    Producto* p = buscarProd(s, clave);
    return p ? productoEliminar(s, p, false) : "El producto ya no existe";
}

string modificarDesdeLinea(Sistema& s, const string& ent, const string& clave, const string& linea) {
    vector<string> c = dividir(linea, '|');
    if (ent == "grupo") {
        Grupo* g = buscarGrupo(s, clave);
        if (g == NULL || c.size() < 7) return "El grupo ya no existe";
        return grupoModificar(s, g, c[2], c[3], c[4], c[5], false);
    }
    if (ent == "investigador") {
        Investigador* i = buscarInv(s, clave);
        if (i == NULL || c.size() < 8) return "El investigador ya no existe";
        return investigadorModificar(s, i, c[2], c[3], c[4], c[5], c[6], false);
    }
    Producto* p = buscarProd(s, clave);
    Producto antes;
    if (p == NULL || !productoDesdeCampos(c, antes)) return "El producto ya no existe";
    return productoModificar(s, p, antes, false);
}

string desactivarEntidad(Sistema& s, const string& ent, const string& clave, bool activo) {
    if (ent == "grupo") {
        Grupo* g = buscarGrupo(s, clave);
        return g ? grupoDesactivar(s, g, activo, false) : "El grupo ya no existe";
    }
    if (ent == "investigador") {
        Investigador* i = buscarInv(s, clave);
        return i ? investigadorDesactivar(s, i, activo, false) : "El investigador ya no existe";
    }
    Producto* p = buscarProd(s, clave);
    return p ? productoDesactivar(s, p, activo, false) : "El producto ya no existe";
}

string restaurarProductoDesdeLinea(Sistema& s, const string& linea) {
    Producto p;
    if (!productoDesdeCampos(dividir(linea, '|'), p)) return "Línea de producto inválida";
    string error = validarProducto(s, p.grupo, p.autores, p.anio);
    if (!error.empty()) return error;
    productoInsertar(s, p);
    return "";
}

string restaurarEntidad(Sistema& s, const Operacion& o) {
    if (o.ent == "grupo") {
        vector<string> c = dividir(o.lineas[0], '|');
        if (c.size() < 7) return "Instantánea inválida";
        Grupo* g = grupoNuevo(c[1], c[2], c[3], c[4], c[5], c[6] == "1");
        listaInsertarFinal(s.grupos, g);
        for (size_t k = 1; k < o.lineas.size(); k++) {
            vector<string> m = dividir(o.lineas[k], '|');
            if (m.size() < 7) continue;
            Integrante* it = new Integrante;
            it->idInv = m[2]; it->vinculacion = m[3]; it->horas = m[4]; it->periodo = m[5];
            it->activo = (m[6] == "1");
            listaInsertarFinal(g->integrantes, it);
        }
        for (size_t k = 0; k < o.productos.size(); k++) {
            string error = restaurarProductoDesdeLinea(s, o.productos[k]);
            if (!error.empty()) return error;
        }
        return "";
    }
    if (o.ent == "investigador") {
        vector<string> c = dividir(o.lineas[0], '|');
        if (c.size() < 8) return "Instantánea inválida";
        listaInsertarFinal(s.investigadores,
                           investigadorNuevo(c[1], c[2], c[3], c[4], c[5], c[6], c[7] == "1"));
        return "";
    }
    return restaurarProductoDesdeLinea(s, o.lineas[0]);
}

string deshacerUltima(Sistema& s) {
    Operacion* o = (Operacion*)pilaDesapilar(s.historial);
    if (o == NULL) return "No hay operaciones para deshacer";
    string error;
    if (o->op == "crear") error = eliminarEntidad(s, o->ent, o->clave);
    else if (o->op == "modificar") error = modificarDesdeLinea(s, o->ent, o->clave, o->lineas[0]);
    else if (o->op == "desactivar") error = desactivarEntidad(s, o->ent, o->clave, o->antesActivo);
    else if (o->op == "eliminar") error = restaurarEntidad(s, *o);
    string msg = error.empty() ? "Deshecho: " + o->op + " " + o->ent + " " + o->clave
                               : "No se pudo deshacer: " + error;
    delete o;
    return msg;
}

// =====================================================================
// 12. PERSISTENCIA (formato PEA-i-TXT v1, el mismo que genera Python)
// =====================================================================
string guardarTxt(Sistema& s, const string& ruta) {
    ofstream f(ruta.c_str(), ios::binary);
    if (!f) return "No se pudo abrir el archivo para escribir: " + ruta;
    int nG = 0, nI = 0, nM = 0, nP = 0;
    f << "#PEA-i-TXT v1\n";
    f << "# Campos separados por |  (ver especificación en Taller2_PEAi.cpp)\n";
    f << "C|" << s.contProd << "|" << s.contInv << "\n";
    for (Nodo* n = s.grupos.cabeza; n != NULL; n = n->sig) { f << lineaG((Grupo*)n->dato) << "\n"; nG++; }
    for (Nodo* n = s.investigadores.cabeza; n != NULL; n = n->sig) { f << lineaI((Investigador*)n->dato) << "\n"; nI++; }
    for (Nodo* n = s.grupos.cabeza; n != NULL; n = n->sig) {
        Grupo* g = (Grupo*)n->dato;
        for (Nodo* m = g->integrantes.cabeza; m != NULL; m = m->sig) {
            f << lineaM(g->codigo, (Integrante*)m->dato) << "\n";
            nM++;
        }
    }
    for (Nodo* n = s.productos.cabeza; n != NULL; n = n->sig) { f << lineaP((Producto*)n->dato) << "\n"; nP++; }
    for (Nodo* n = s.importaciones.frente; n != NULL; n = n->sig) {
        Importacion* q = (Importacion*)n->dato;
        f << "Q|" << quitarSep(q->tipo) << "|" << quitarSep(q->origen) << "|" << quitarSep(q->estado)
          << "|" << quitarSep(q->modo) << "|" << quitarSep(q->codigo) << "\n";
    }
    f << "FIN|" << nG << "|" << nI << "|" << nM << "|" << nP << "\n";
    f.close();
    return "";
}

string cargarTxt(Sistema& s, const string& ruta, vector<string>& avisos) {
    ifstream f(ruta.c_str(), ios::binary);
    if (!f) return "No se pudo abrir el archivo: " + ruta;
    vector<string> lineas;
    string linea;
    while (getline(f, linea)) {
        if (!linea.empty() && linea[linea.size() - 1] == '\r') linea.erase(linea.size() - 1);
        lineas.push_back(linea);
    }
    if (!lineas.empty() && lineas[0].size() >= 3 && (unsigned char)lineas[0][0] == 0xEF)
        lineas[0].erase(0, 3);                                   // BOM UTF-8
    if (lineas.empty() || lineas[0].compare(0, 10, "#PEA-i-TXT") != 0)
        return "El archivo no tiene el formato PEA-i-TXT";
    sistemaVaciar(s);
    int nG = 0, nI = 0, nM = 0, nP = 0, fG = -1, fI = -1, fM = -1, fP = -1;
    const char* orden[] = {"C", "G", "I", "M", "P", "Q", "FIN"};
    for (int pasada = 0; pasada < 7; pasada++) {
        for (size_t n = 0; n < lineas.size(); n++) {
            if (lineas[n].empty() || lineas[n][0] == '#') continue;
            vector<string> c = dividir(lineas[n], '|');
            if (c[0] != orden[pasada]) continue;
            ostringstream pos;
            pos << "Línea " << (n + 1) << " inválida";
            if (c[0] == "C" && c.size() >= 3) {
                s.contProd = atoi(c[1].c_str());
                s.contInv = atoi(c[2].c_str());
            } else if (c[0] == "G" && c.size() >= 7) {
                listaInsertarFinal(s.grupos, grupoNuevo(c[1], c[2], c[3], c[4], c[5], c[6] == "1"));
                nG++;
            } else if (c[0] == "I" && c.size() >= 8) {
                listaInsertarFinal(s.investigadores,
                                   investigadorNuevo(c[1], c[2], c[3], c[4], c[5], c[6], c[7] == "1"));
                nI++;
            } else if (c[0] == "M" && c.size() >= 7) {
                Grupo* g = buscarGrupo(s, c[1]);
                if (g == NULL) { avisos.push_back(pos.str() + " (integrante de grupo inexistente)"); continue; }
                Integrante* m = new Integrante;
                m->idInv = c[2]; m->vinculacion = c[3]; m->horas = c[4]; m->periodo = c[5];
                m->activo = (c[6] == "1");
                listaInsertarFinal(g->integrantes, m);
                nM++;
            } else if (c[0] == "P") {
                Producto p;
                if (!productoDesdeCampos(c, p)) { avisos.push_back(pos.str()); continue; }
                string error = validarProducto(s, p.grupo, p.autores, p.anio);
                if (!error.empty()) { avisos.push_back("Producto " + p.id + " omitido: " + error); continue; }
                productoInsertar(s, p);
                nP++;
            } else if (c[0] == "Q" && c.size() >= 6) {
                Importacion* q = new Importacion;
                q->tipo = c[1]; q->origen = c[2]; q->estado = c[3].empty() ? "pendiente" : c[3];
                q->modo = c[4]; q->codigo = c[5];
                colaEncolar(s.importaciones, q);
            } else if (c[0] == "FIN" && c.size() >= 5) {
                fG = atoi(c[1].c_str()); fI = atoi(c[2].c_str());
                fM = atoi(c[3].c_str()); fP = atoi(c[4].c_str());
            } else {
                avisos.push_back(pos.str());
            }
        }
    }
    if (fG >= 0 && (fG != nG || fI != nI || fM != nM || fP != nP))
        avisos.push_back("Los totales del archivo (FIN) no coinciden con lo leído: puede estar incompleto");
    return "";
}

// =====================================================================
// 13. PANTALLAS DE LISTADO
// =====================================================================
void listarGrupos(bool conInactivos) {
    vector<Grupo*> gs = arregloGrupos(S.grupos, !conInactivos);
    cout << "\n " << pad("#", 3) << pad("Código", 11) << pad("Nombre", 40) << pad("Líder", 26)
         << pad("Cat.", 11) << pad("Integ.", 7) << pad("Prod.", 6) << "Activo\n";
    cout << " " << string(112, '-') << "\n";
    for (size_t k = 0; k < gs.size(); k++) {
        Grupo* g = gs[k];
        cout << " " << pad(aTexto(k + 1), 3) << pad(g->codigo, 11) << pad(g->nombre, 40)
             << pad(g->lider, 26) << pad(g->categoria, 11) << pad(aTexto(g->integrantes.tam), 7)
             << pad(aTexto(g->productos.tam), 6) << siNo(g->activo) << "\n";
    }
    cout << " Total: " << gs.size() << " grupos\n";
}

void listarInvestigadores(const string& filtroTexto, bool conInactivos) {
    vector<Investigador*> is = arregloInv(S.investigadores, !conInactivos);
    cout << "\n " << pad("ID", 10) << pad("Nombre", 36) << pad("Cod. CvLAC", 12) << pad("Categoría", 24)
         << pad("Prod.", 6) << "Activo\n";
    cout << " " << string(96, '-') << "\n";
    int mostrados = 0;
    for (size_t k = 0; k < is.size(); k++) {
        Investigador* i = is[k];
        if (!contiene(i->nombre, filtroTexto) && !contiene(i->id, filtroTexto)) continue;
        cout << " " << pad(i->id, 10) << pad(i->nombre, 36) << pad(i->codRh, 12)
             << pad(i->categoria, 24) << pad(aTexto(i->productos.tam), 6) << siNo(i->activo) << "\n";
        mostrados++;
    }
    cout << " Total: " << mostrados << " investigadores\n";
}

void listarIntegrantes(Grupo* g) {
    cout << "\n " << pad("ID", 10) << pad("Nombre", 36) << pad("Vinculación", 22) << pad("Horas", 7)
         << pad("Periodo", 20) << "Activo\n";
    cout << " " << string(102, '-') << "\n";
    vector<Integrante*> ms = arregloInteg(g->integrantes);
    for (size_t k = 0; k < ms.size(); k++)
        cout << " " << pad(ms[k]->idInv, 10) << pad(nombreInv(S, ms[k]->idInv), 36)
             << pad(ms[k]->vinculacion, 22) << pad(ms[k]->horas, 7) << pad(ms[k]->periodo, 20)
             << siNo(ms[k]->activo) << "\n";
    cout << " Total: " << ms.size() << " integrantes\n";
}

void listarProductosPaginado(const vector<Producto*>& ps) {
    const int POR_PAGINA = 20;
    size_t k = 0;
    while (k < ps.size()) {
        cout << "\n " << pad("ID", 10) << pad("Tipo", 22) << pad("Cat.", 11) << pad("Año", 6)
             << pad("Val.", 5) << pad("Grupo", 11) << "Título\n";
        cout << " " << string(112, '-') << "\n";
        for (int n = 0; n < POR_PAGINA && k < ps.size(); n++, k++) {
            Producto* p = ps[k];
            cout << " " << pad(p->id, 10) << pad(p->tipo, 22) << pad(p->categoria, 11)
                 << pad(aTexto(p->anio), 6) << pad(p->validado ? "Sí" : "No", 5)
                 << pad(p->grupo, 11) << cortar(p->titulo, 60) << (p->activo ? "" : "  [inactivo]") << "\n";
        }
        cout << " Mostrando " << k << " de " << ps.size() << " productos\n";
        if (k < ps.size()) {
            string r = leerLinea(" [Enter = siguiente página, q = terminar] ");
            if (!r.empty() && (r[0] == 'q' || r[0] == 'Q')) return;
        }
    }
    if (ps.empty()) cout << "\n (No hay productos con esos filtros)\n";
}

void verProducto(Producto* p) {
    cout << "\n ID ............ " << p->id << "\n Título ........ " << p->titulo
         << "\n Tipo .......... " << p->tipo << "\n Categoría ..... " << p->categoria
         << "\n Año ........... " << p->anio << "\n Validado ...... " << siNo(p->validado)
         << "\n Grupo ......... " << p->grupo << "\n Activo ........ " << siNo(p->activo)
         << "\n Autores ....... ";
    if (p->autores.empty()) cout << "N/D";
    for (size_t k = 0; k < p->autores.size(); k++)
        cout << (k ? ", " : "") << nombreInv(S, p->autores[k]) << " (" << p->autores[k] << ")";
    cout << "\n";
}

// =====================================================================
// 14. SELECCIÓN DE REGISTROS Y FORMULARIOS
// =====================================================================
Grupo* elegirGrupo(bool mostrarLista) {
    if (S.grupos.tam == 0) { cout << "  No hay grupos registrados.\n"; return NULL; }
    if (mostrarLista) listarGrupos(true);
    string e = leerLinea("\n Código del grupo o número de la lista (Enter = cancelar): ");
    if (e.empty()) return NULL;
    vector<Grupo*> gs = arregloGrupos(S.grupos, false);
    char* fin = NULL;
    long v = strtol(e.c_str(), &fin, 10);
    if (*fin == '\0' && v >= 1 && v <= (long)gs.size()) return gs[v - 1];
    Grupo* g = buscarGrupo(S, e);
    if (g == NULL) cout << "  No se encontró ese grupo.\n";
    return g;
}

Investigador* elegirInvestigador() {
    string e = leerLinea("\n ID (ej. INV-0007) o parte del nombre (Enter = cancelar): ");
    if (e.empty()) return NULL;
    Investigador* i = buscarInv(S, e);
    if (i != NULL) return i;
    vector<Investigador*> todos = arregloInv(S.investigadores, false), coinc;
    for (size_t k = 0; k < todos.size(); k++)
        if (contiene(todos[k]->nombre, e)) coinc.push_back(todos[k]);
    if (coinc.empty()) { cout << "  No se encontró ningún investigador.\n"; return NULL; }
    if (coinc.size() == 1) return coinc[0];
    cout << "  Hay " << coinc.size() << " coincidencias:\n";
    size_t limite = coinc.size() < 15 ? coinc.size() : 15;
    for (size_t k = 0; k < limite; k++)
        cout << "   " << (k + 1) << ". " << coinc[k]->id << "  " << coinc[k]->nombre << "\n";
    if (coinc.size() > limite) cout << "   ... escriba más letras para acotar.\n";
    int op = leerEntero("  Elija un número (0 = cancelar): ", 0, (int)limite);
    return op == 0 ? NULL : coinc[op - 1];
}

Producto* elegirProducto() {
    string id = leerLinea("\n ID del producto (ej. PRD-0012, Enter = cancelar): ");
    if (id.empty()) return NULL;
    Producto* p = buscarProd(S, id);
    if (p == NULL) cout << "  No se encontró ese producto.\n";
    return p;
}

vector<string> tiposConocidos() {
    set<string> t;
    const char* base[] = {"Artículo", "Libro", "Capítulo de libro", "Software", "Proyecto",
                          "Evento", "Trabajo de grado", "Patente"};
    for (int k = 0; k < 8; k++) t.insert(base[k]);
    for (Nodo* n = S.productos.cabeza; n != NULL; n = n->sig) t.insert(((Producto*)n->dato)->tipo);
    return vector<string>(t.begin(), t.end());
}

string elegirTipo(const string& actual, bool permitirVacio) {
    vector<string> ts = tiposConocidos();
    for (size_t k = 0; k < ts.size(); k++) cout << "   " << pad(aTexto(k + 1), 4) << ts[k] << "\n";
    string e = leerLinea(actual.empty() ? "  Tipo (número de la lista o texto nuevo): "
                                        : "  Tipo (número, texto nuevo o Enter = " + actual + "): ");
    if (e.empty()) return actual;
    char* fin = NULL;
    long v = strtol(e.c_str(), &fin, 10);
    if (*fin == '\0' && v >= 1 && v <= (long)ts.size()) return ts[v - 1];
    (void)permitirVacio;
    return e;
}

vector<string> leerAutores(const string& actualTexto) {
    string e = leerLinea("  IDs de autores separados por coma (ej. INV-0001,INV-0004)" +
                         string(actualTexto.empty() ? ", Enter = ninguno: " : " [" + actualTexto + "]: "));
    if (e.empty() && !actualTexto.empty()) e = actualTexto;
    vector<string> r;
    vector<string> partes = dividir(e, ',');
    for (size_t k = 0; k < partes.size(); k++) {
        string id = recortarEspacios(partes[k]);
        if (!id.empty()) r.push_back(id);
    }
    return r;
}

// =====================================================================
// 15. MENÚS DE CRUD
// =====================================================================
void menuIntegrantes(Grupo* g) {
    while (true) {
        titulo("Integrantes del grupo " + g->codigo + " - " + cortar(g->nombre, 40));
        listarIntegrantes(g);
        cout << "\n 1. Agregar integrante\n 2. Modificar vinculación/horas/periodo\n"
                " 3. Activar / Desactivar\n 4. Retirar del grupo\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 4);
        if (op == 0) return;
        if (op == 1) {
            Investigador* i = elegirInvestigador();
            if (i == NULL) continue;
            string vinc = leerLinea("  Vinculación [Integrante]: ");
            string horas = leerLinea("  Horas de dedicación [N/D]: ");
            string per = leerLinea("  Periodo [Actual]: ");
            string error = integranteAgregar(S, g, i->id, vinc.empty() ? "Integrante" : vinc,
                                             horas.empty() ? "N/D" : horas, per.empty() ? "Actual" : per);
            cout << (error.empty() ? "  Integrante agregado.\n" : "  Error: " + error + "\n");
            if (error.empty()) SUCIO = true;
        } else {
            string id = leerLinea("  ID del investigador integrante: ");
            Integrante* m = buscarInteg(g, id);
            if (m == NULL) { cout << "  No es integrante de este grupo.\n"; continue; }
            if (op == 2) {
                m->vinculacion = leerCampo("  Vinculación", m->vinculacion);
                m->horas = leerCampo("  Horas", m->horas);
                m->periodo = leerCampo("  Periodo", m->periodo);
                cout << "  Integrante modificado.\n";
            } else if (op == 3) {
                m->activo = !m->activo;
                cout << "  Integrante " << (m->activo ? "activado" : "desactivado") << ".\n";
            } else if (confirmar("  ¿Retirar del grupo a " + nombreInv(S, id) + "?")) {
                integranteEliminar(g, id);
                cout << "  Integrante retirado.\n";
            }
            SUCIO = true;
        }
    }
}

void menuGrupos() {
    while (true) {
        titulo("GRUPOS DE INVESTIGACIÓN");
        cout << " 1. Listar grupos\n 2. Crear grupo\n 3. Ver detalle (integrantes y productos)\n"
                " 4. Modificar grupo\n 5. Activar / Desactivar\n 6. Eliminar grupo\n"
                " 7. Gestionar integrantes\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 7);
        if (op == 0) return;
        if (op == 1) { listarGrupos(true); esperarEnter(); continue; }
        if (op == 2) {
            string cod = leerLinea("  Código (ej. COL0012345): ");
            string nom = leerLinea("  Nombre: ");
            if (cod.empty() || nom.empty()) { cout << "  Código y nombre son obligatorios.\n"; continue; }
            string lid = leerLinea("  Líder [N/D]: ");
            string cat = leerLinea("  Categoría (A1, A, B, C, Reconocido) [Sin categoría]: ");
            string url = leerLinea("  URL GrupLAC (opcional): ");
            string error = grupoCrear(S, cod, nom, lid.empty() ? "N/D" : lid,
                                      cat.empty() ? "Sin categoría" : cat, url, true);
            cout << (error.empty() ? "  Grupo creado.\n" : "  Error: " + error + "\n");
            if (error.empty()) SUCIO = true;
            continue;
        }
        Grupo* g = elegirGrupo(true);
        if (g == NULL) continue;
        if (op == 3) {
            cout << "\n Grupo: " << g->codigo << " - " << g->nombre << "\n Líder: " << g->lider
                 << "   Categoría: " << g->categoria << "   Activo: " << siNo(g->activo) << "\n URL: " << g->url << "\n";
            listarIntegrantes(g);
            vector<Producto*> ps = arregloProd(g->productos);
            cout << "\n Productos del grupo: " << ps.size() << "\n";
            if (!ps.empty() && confirmar(" ¿Ver el listado de productos?")) listarProductosPaginado(ps);
        } else if (op == 4) {
            string nom = leerCampo("  Nombre", g->nombre);
            string lid = leerCampo("  Líder", g->lider);
            string cat = leerCampo("  Categoría", g->categoria);
            string url = leerCampo("  URL", g->url);
            grupoModificar(S, g, nom, lid, cat, url, true);
            cout << "  Grupo modificado.\n";
            SUCIO = true;
        } else if (op == 5) {
            grupoDesactivar(S, g, !g->activo, true);
            cout << "  Grupo " << (g->activo ? "activado" : "desactivado") << ".\n";
            SUCIO = true;
        } else if (op == 6) {
            int n = g->productos.tam;
            if (n == 0) {
                if (confirmar("  ¿Eliminar definitivamente el grupo " + g->codigo + "?")) {
                    grupoEliminar(S, g, true);
                    cout << "  Grupo eliminado (puede deshacerlo).\n";
                    SUCIO = true;
                }
            } else {
                cout << "\n  El grupo " << g->codigo << " tiene " << n << " productos asociados.\n"
                     << "  - Si responde SÍ se elimina el grupo junto con sus " << n << " productos y sus\n"
                     << "    integrantes. Se puede deshacer de una sola vez.\n"
                     << "  - Si responde NO se cancela. Para ocultarlo sin perder datos use 'Desactivar'.\n";
                if (confirmar("  ¿Eliminar el grupo y sus productos?")) {
                    grupoEliminarCascada(S, g);
                    cout << "  Grupo y " << n << " productos eliminados (puede deshacerlo).\n";
                    SUCIO = true;
                }
            }
        } else if (op == 7) {
            menuIntegrantes(g);
        }
        if (op != 7 && op != 3) esperarEnter();
    }
}

void menuInvestigadores() {
    while (true) {
        titulo("INVESTIGADORES");
        cout << " 1. Listar (con búsqueda opcional)\n 2. Crear investigador\n 3. Ver detalle\n"
                " 4. Modificar\n 5. Activar / Desactivar\n 6. Eliminar\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 6);
        if (op == 0) return;
        if (op == 1) {
            string f = leerLinea("  Buscar por nombre o ID (Enter = todos): ");
            listarInvestigadores(f, true);
            esperarEnter();
            continue;
        }
        if (op == 2) {
            string nom = leerLinea("  Nombre completo: ");
            if (nom.empty()) { cout << "  El nombre es obligatorio.\n"; continue; }
            string rh = leerLinea("  Código CvLAC (cod_rh, opcional): ");
            string em = leerLinea("  Correo (opcional): ");
            string fo = leerLinea("  Formación (Pregrado, Maestría, Doctorado...): ");
            string ca = leerLinea("  Categoría [Sin categoría]: ");
            investigadorCrear(S, nom, rh, em, fo, ca.empty() ? "Sin categoría" : ca, true);
            cout << "  Investigador creado.\n";
            SUCIO = true;
            esperarEnter();
            continue;
        }
        Investigador* i = elegirInvestigador();
        if (i == NULL) continue;
        if (op == 3) {
            cout << "\n ID: " << i->id << "\n Nombre: " << i->nombre << "\n CvLAC: " << i->codRh
                 << "\n Correo: " << i->email << "\n Formación: " << i->formacion
                 << "\n Categoría: " << i->categoria << "\n Activo: " << siNo(i->activo)
                 << "\n Productos: " << i->productos.tam << "\n";
            vector<Producto*> ps = arregloProd(i->productos);
            if (!ps.empty() && confirmar(" ¿Ver sus productos?")) listarProductosPaginado(ps);
        } else if (op == 4) {
            string nom = leerCampo("  Nombre", i->nombre);
            string rh = leerCampo("  Código CvLAC", i->codRh);
            string em = leerCampo("  Correo", i->email);
            string fo = leerCampo("  Formación", i->formacion);
            string ca = leerCampo("  Categoría", i->categoria);
            investigadorModificar(S, i, nom, rh, em, fo, ca, true);
            cout << "  Investigador modificado.\n";
            SUCIO = true;
        } else if (op == 5) {
            investigadorDesactivar(S, i, !i->activo, true);
            cout << "  Investigador " << (i->activo ? "activado" : "desactivado") << ".\n";
            SUCIO = true;
        } else if (op == 6) {
            if (confirmar("  ¿Eliminar definitivamente a " + i->nombre + "?")) {
                string error = investigadorEliminar(S, i, true);
                cout << (error.empty() ? "  Investigador eliminado (puede deshacerlo).\n" : "  No se pudo: " + error + "\n");
                if (error.empty()) SUCIO = true;
            }
        }
        esperarEnter();
    }
}

void consultarProductos() {
    Filtros f = filtrosNuevos();
    aplicarVentana(f);
    cout << "\n Filtros (Enter = sin filtro). Ventana de observación actual: ";
    cout << (VENTANA_N == 0 ? string("histórico completo") : "últimos " + aTexto(VENTANA_N) + " años") << "\n";
    string g = leerLinea("  Código de grupo: ");
    string i = leerLinea("  ID de investigador: ");
    string t = leerLinea("  ¿Filtrar por tipo? (s/n): ");
    if (!t.empty() && (t[0] == 's' || t[0] == 'S')) f.tipo = elegirTipo("", true);
    string v = leerLinea("  ¿Solo validados? (s/n): ");
    string texto = leerLinea("  Texto contenido en el título: ");
    string x = leerLinea("  ¿Incluir inactivos? (s/n): ");
    f.grupo = g;
    f.inv = i;
    f.soloValidados = (!v.empty() && (v[0] == 's' || v[0] == 'S'));
    f.soloActivos = !(!x.empty() && (x[0] == 's' || x[0] == 'S'));
    vector<Producto*> todos = cuboConsultar(S.cubo, f), ps;
    for (size_t k = 0; k < todos.size(); k++)
        if (contiene(todos[k]->titulo, texto)) ps.push_back(todos[k]);
    sort(ps.begin(), ps.end(), menorProductoId);
    listarProductosPaginado(ps);
}

void menuProductos() {
    while (true) {
        titulo("PRODUCTOS DE INVESTIGACIÓN");
        cout << " 1. Consultar / filtrar (usa el hipercubo)\n 2. Ver detalle de un producto\n"
                " 3. Crear producto\n 4. Modificar producto\n 5. Validar / Invalidar\n"
                " 6. Activar / Desactivar\n 7. Eliminar producto\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 7);
        if (op == 0) return;
        if (op == 1) { consultarProductos(); esperarEnter(); continue; }
        if (op == 3) {
            Grupo* g = elegirGrupo(true);
            if (g == NULL) continue;
            string tit = leerLinea("  Título: ");
            if (tit.empty()) { cout << "  El título es obligatorio.\n"; continue; }
            string tipo = elegirTipo("", false);
            if (tipo.empty()) { cout << "  El tipo es obligatorio.\n"; continue; }
            string cat = leerLinea("  Categoría (A1, A2, B, C) [Sin categoría]: ");
            int anio = leerEntero("  Año (1950-" + aTexto(anioActual() + 1) + "): ", 1950, anioActual() + 1);
            bool val = confirmar("  ¿Validado?");
            vector<string> aut = leerAutores("");
            string error = productoCrear(S, g->codigo, tit, tipo, anio, cat.empty() ? "Sin categoría" : cat, val, aut, true);
            cout << (error.empty() ? "  Producto creado.\n" : "  Error: " + error + "\n");
            if (error.empty()) SUCIO = true;
            esperarEnter();
            continue;
        }
        Producto* p = elegirProducto();
        if (p == NULL) continue;
        if (op == 2) {
            verProducto(p);
        } else if (op == 4) {
            verProducto(p);
            Producto n = *p;
            n.titulo = leerCampo("  Título", p->titulo);
            n.tipo = elegirTipo(p->tipo, false);
            n.categoria = leerCampo("  Categoría", p->categoria);
            n.anio = leerEntero("  Año [" + aTexto(p->anio) + "] (escriba el año): ", 1950, anioActual() + 1);
            n.validado = confirmar("  ¿Validado? (actual: " + siNo(p->validado) + ")");
            n.grupo = leerCampo("  Código de grupo", p->grupo);
            n.autores = leerAutores(unir(p->autores, ","));
            string error = productoModificar(S, p, n, true);
            cout << (error.empty() ? "  Producto modificado.\n" : "  Error: " + error + "\n");
            if (error.empty()) SUCIO = true;
        } else if (op == 5) {
            Producto n = *p;
            n.validado = !p->validado;
            productoModificar(S, p, n, true);
            cout << "  Producto " << (p->validado ? "validado" : "marcado como no validado") << ".\n";
            SUCIO = true;
        } else if (op == 6) {
            productoDesactivar(S, p, !p->activo, true);
            cout << "  Producto " << (p->activo ? "activado" : "desactivado") << ".\n";
            SUCIO = true;
        } else if (op == 7) {
            if (confirmar("  ¿Eliminar definitivamente " + p->id + "?")) {
                productoEliminar(S, p, true);
                cout << "  Producto eliminado (puede deshacerlo).\n";
                SUCIO = true;
            }
        }
        esperarEnter();
    }
}

// =====================================================================
// 16. ESTADÍSTICAS (resumen de datos: tablas y números)
// =====================================================================
string etiquetaDimension(const string& dim, const string& valor) {
    if (dim == "grupo") {
        Grupo* g = buscarGrupo(S, valor);
        return g ? g->nombre : valor;
    }
    if (dim == "inv") return valor == "N/D" ? valor : nombreInv(S, valor);
    return valor;
}

void imprimirTabla(const string& nombre, const string& dim, const map<string, int>& datos) {
    cout << "\n --- " << nombre << " ---\n";
    if (datos.empty()) { cout << "   (sin datos)\n"; return; }
    vector<pair<string, int> > filas;
    if (dim == "anio") {                                       // histograma sin huecos
        int a0 = atoi(datos.begin()->first.c_str()), a1 = atoi(datos.rbegin()->first.c_str());
        for (int a = a0; a <= a1; a++) {
            map<string, int>::const_iterator it = datos.find(aTexto(a));
            filas.push_back(make_pair(aTexto(a), it == datos.end() ? 0 : it->second));
        }
    } else {
        for (map<string, int>::const_iterator it = datos.begin(); it != datos.end(); ++it)
            filas.push_back(make_pair(it->first, it->second));
        sort(filas.begin(), filas.end(), mayorCuenta);
        if (filas.size() > 10) {
            int resto = 0;
            for (size_t k = 9; k < filas.size(); k++) resto += filas[k].second;
            filas.resize(9);
            filas.push_back(make_pair(string("Otros"), resto));
        }
    }
    int maximo = 0, suma = 0;
    for (size_t k = 0; k < filas.size(); k++) {
        if (filas[k].second > maximo) maximo = filas[k].second;
        suma += filas[k].second;
    }
    for (size_t k = 0; k < filas.size(); k++) {
        int barra = maximo > 0 ? (filas[k].second * 36) / maximo : 0;
        if (filas[k].second > 0 && barra == 0) barra = 1;
        string et = filas[k].first == "Otros" ? string("Otros") : etiquetaDimension(dim, filas[k].first);
        cout << "   " << pad(et, 44) << padIzq(aTexto(filas[k].second), 5) << "  " << string(barra, '#') << "\n";
    }
    cout << "   " << pad("Suma", 44) << padIzq(aTexto(suma), 5) << "\n";
}

void mostrarEstadisticas(const string& cabecera, const Filtros& f, const string dims[], const string nombres[], int n) {
    vector<Producto*> ps = cuboConsultar(S.cubo, f);
    int validados = 0;
    for (size_t k = 0; k < ps.size(); k++)
        if (ps[k]->validado) validados++;
    titulo(cabecera);
    cout << " Ventana de observación: ";
    if (VENTANA_N == 0) cout << "histórico completo\n";
    else cout << "últimos " << VENTANA_N << " años (" << f.anioDesde << "-" << f.anioHasta << ")\n";
    cout << " Productos: " << ps.size() << "   |   Validados: " << validados
         << "   |   No validados: " << (int)ps.size() - validados << "\n";
    for (int k = 0; k < n; k++) imprimirTabla(nombres[k], dims[k], cuboResumen(S.cubo, dims[k], f));
}

void menuEstadisticas() {
    while (true) {
        titulo("ESTADÍSTICAS");
        cout << " 1. Vista global\n 2. Vista por grupo\n 3. Vista por investigador\n"
                " 4. Vista por producto (tipo)\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 4);
        if (op == 0) return;
        Filtros f = filtrosNuevos();
        aplicarVentana(f);
        if (op == 1) {
            string d[] = {"anio", "tipo", "categoria", "grupo"};
            string nm[] = {"Productos por año (histograma)", "Por tipo", "Por categoría", "Por grupo"};
            mostrarEstadisticas("VISTA GLOBAL", f, d, nm, 4);
        } else if (op == 2) {
            Grupo* g = elegirGrupo(true);
            if (g == NULL) continue;
            f.grupo = g->codigo;
            string d[] = {"anio", "tipo", "categoria", "inv"};
            string nm[] = {"Productos por año (histograma)", "Por tipo", "Por categoría", "Por investigador"};
            mostrarEstadisticas("VISTA POR GRUPO: " + g->codigo + " - " + cortar(g->nombre, 40), f, d, nm, 4);
        } else if (op == 3) {
            Investigador* i = elegirInvestigador();
            if (i == NULL) continue;
            f.inv = i->id;
            string d[] = {"anio", "tipo", "categoria", "grupo"};
            string nm[] = {"Productos por año (histograma)", "Por tipo", "Por categoría", "Por grupo"};
            mostrarEstadisticas("VISTA POR INVESTIGADOR: " + i->nombre, f, d, nm, 4);
        } else {
            string t = elegirTipo("", true);
            if (t.empty()) continue;
            f.tipo = t;
            string d[] = {"anio", "categoria", "grupo", "inv"};
            string nm[] = {"Productos por año (histograma)", "Por categoría", "Por grupo", "Por investigador"};
            mostrarEstadisticas("VISTA POR PRODUCTO (tipo: " + t + ")", f, d, nm, 4);
        }
        esperarEnter();
    }
}

// =====================================================================
// 17a. IMPORTAR DATOS DELEGANDO EN PYTHON (scraping, HTML, PDF, CSV)
// =====================================================================
// Protege el argumento para la línea de comandos del sistema operativo.
string comillas(const string& s) {
    string r;
#ifdef _WIN32
    for (size_t i = 0; i < s.size(); i++)
        if (s[i] != '"') r += s[i];
    return "\"" + r + "\"";
#else
    for (size_t i = 0; i < s.size(); i++) {
        if (s[i] == '\'') r += "'\\''";
        else r += s[i];
    }
    return "'" + r + "'";
#endif
}

string quitarComillasExternas(string s) {
    while (!s.empty() && (s[0] == '"' || s[0] == '\'')) s.erase(0, 1);
    while (!s.empty() && (s[s.size() - 1] == '"' || s[s.size() - 1] == '\'')) s.erase(s.size() - 1);
    return s;
}

// Comprueba que el comando de Python funciona (ejecuta "<cmd> --version" en silencio).
bool pythonFunciona(const string& cmd) {
    string c = comillas(cmd) + " --version";
#ifdef _WIN32
    c = "\"" + c + " > nul 2>&1\"";
#else
    c += " > /dev/null 2>&1";
#endif
    return system(c.c_str()) == 0;
}

// Busca un Python que funcione: el configurado, py, python, python3 y las rutas típicas de
// Windows. (En Windows, "python" suele ser un acceso directo a la Microsoft Store que NO sirve.)
bool detectarPython() {
    vector<string> candidatos;
    candidatos.push_back(CMD_PYTHON);
    candidatos.push_back("py");
    candidatos.push_back("python");
    candidatos.push_back("python3");
#ifdef _WIN32
    const char* local = getenv("LOCALAPPDATA");
    if (local != NULL) {
        string base(local);
        const char* versiones[] = {"314", "313", "312", "311", "310"};
        for (int k = 0; k < 5; k++) {
            string v = versiones[k];
            candidatos.push_back(base + "\\Python\\pythoncore-3." + v.substr(1) + "-64\\python.exe");
            candidatos.push_back(base + "\\Programs\\Python\\Python" + v + "\\python.exe");
        }
    }
#endif
    for (size_t k = 0; k < candidatos.size(); k++) {
        if (pythonFunciona(candidatos[k])) {
            if (candidatos[k] != CMD_PYTHON) cout << "  Entorno de ejecución detectado automáticamente.\n";
            CMD_PYTHON = candidatos[k];
            PYTHON_VERIFICADO = true;
            return true;
        }
    }
    return false;
}

// 1) guarda los datos actuales en un archivo temporal, 2) ejecuta Python en modo consola
// con los argumentos dados, 3) recarga el resultado. Devuelve true si todo salió bien.
bool ejecutarPython(const string& argumentos) {
    if (!PYTHON_VERIFICADO && !detectarPython()) {
        cout << "\n  No se encontró el entorno de ejecución del módulo de importación.\n"
                "  Verifique su instalación o escriba la ruta del ejecutable en la opción 4.\n";
        return false;
    }
    ifstream existe(SCRIPT_PY.c_str());
    if (!existe) {
        cout << "\n  No se encuentra '" << SCRIPT_PY << "' en la carpeta desde donde se ejecuta el programa.\n"
                "  Copie el archivo junto al ejecutable o escriba su ruta completa en la opción 4.\n";
        return false;
    }
    existe.close();
    string error = guardarTxt(S, ARCHIVO_INTERCAMBIO);
    if (!error.empty()) { cout << "  " << error << "\n"; return false; }
    string cmd = comillas(CMD_PYTHON) + " " + comillas(SCRIPT_PY) + " --cli --datos " +
                 comillas(ARCHIVO_INTERCAMBIO) + " " + argumentos;
#ifdef _WIN32
    cmd = "\"" + cmd + "\"";            // cmd.exe: comillas externas para varios argumentos entre comillas
#endif
    cout << "\n  Ejecutando el módulo de importación... (puede tardar unos segundos)\n\n";
    int rc = system(cmd.c_str());
    cout << "\n";
    if (rc != 0) {
        remove(ARCHIVO_INTERCAMBIO.c_str());
        cout << "  El módulo de importación terminó con error (código " << rc << "). Revise:\n"
             << "   1) Que el entorno de ejecución del módulo esté bien instalado (opción 4).\n"
             << "   2) Que '" << SCRIPT_PY << "' esté en la carpeta del programa (o use la opción 4).\n"
             << "   3) Las librerías:  pip install requests beautifulsoup4 pypdf\n"
             << "  Sus datos en memoria no se modificaron.\n";
        return false;
    }
    vector<string> avisos;
    error = cargarTxt(S, ARCHIVO_INTERCAMBIO, avisos);
    remove(ARCHIVO_INTERCAMBIO.c_str());
    if (!error.empty()) { cout << "  " << error << "\n"; return false; }
    SUCIO = true;
    cout << "  Datos actualizados desde el módulo de importación: " << S.grupos.tam << " grupos, " << S.investigadores.tam
         << " investigadores, " << S.productos.tam << " productos, cola: " << S.importaciones.tam << ".\n"
         << "  (Use Archivo > Guardar para conservarlos.)\n";
    for (size_t k = 0; k < avisos.size() && k < 5; k++) cout << "  ! " << avisos[k] << "\n";
    return true;
}

// Pregunta qué contiene la fuente. Devuelve los argumentos de --modo / --grupo para Python.
bool elegirContenido(string& argumentos) {
    cout << "\n  ¿Qué contiene la fuente?\n"
            "   1. Detectar automáticamente (listados de SCIENTI: grupos o investigadores)\n"
            "   2. El detalle de UN grupo (GrupLAC: integrantes y productos)\n"
            "   3. El currículo de UN investigador (CvLAC)\n";
    int m = leerEntero("  Opción: ", 1, 3);
    if (m == 1) { argumentos = " --modo auto"; return true; }
    if (m == 2) { argumentos = " --modo grupo"; return true; }
    cout << "  Los productos del investigador se asociarán a un grupo:\n";
    Grupo* g = elegirGrupo(true);
    if (g == NULL) return false;
    argumentos = " --modo investigador --grupo " + comillas(g->codigo);
    return true;
}

void importarDesdeUrl() {
    string url = leerLinea("\n  Pegue la URL de SCIENTI (Enter = cancelar): ");
    if (url.empty()) return;
    string modo;
    if (!elegirContenido(modo)) return;
    ejecutarPython("--importar url " + comillas(url) + modo);
}

void importarDesdeArchivo() {
    string ruta = quitarComillasExternas(leerLinea("\n  Ruta del archivo HTML, PDF o CSV (Enter = cancelar): "));
    if (ruta.empty()) return;
    string bajo = minusculas(ruta), tipo = "html";
    if (bajo.size() > 4 && bajo.compare(bajo.size() - 4, 4, ".csv") == 0) tipo = "csv";
    else if (bajo.size() > 4 && bajo.compare(bajo.size() - 4, 4, ".pdf") == 0) tipo = "pdf";
    string modo;
    if (tipo != "csv" && !elegirContenido(modo)) return;
    ejecutarPython("--importar " + tipo + " " + comillas(ruta) + modo);
}

void procesarColaConPython() {
    if (colaVacia(S.importaciones)) { cout << "  La cola está vacía.\n"; return; }
    cout << "\n  Se descargarán " << S.importaciones.tam << " páginas de SCIENTI, una a una con 2 s de pausa.\n";
    if (confirmar("  ¿Continuar?")) ejecutarPython("--procesar-cola");
}

void menuImportar() {
    while (true) {
        titulo("IMPORTAR DATOS (URL, HTML, PDF, CSV)");
        cout << " Páginas pendientes en la cola: " << S.importaciones.tam << "\n\n"
                " 1. Importar desde una URL de SCIENTI (listado de grupos, grupo o CvLAC)\n"
                " 2. Importar desde un archivo (HTML guardado, PDF o CSV)\n"
                " 3. Procesar toda la cola (descarga el detalle de cada grupo)\n"
                " 4. Configurar el módulo de importación (ejecutable y ruta del script)\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 4);
        if (op == 0) return;
        if (op == 1) importarDesdeUrl();
        else if (op == 2) importarDesdeArchivo();
        else if (op == 3) procesarColaConPython();
        else {
            string c = leerLinea("  Ejecutable del módulo (Enter = detección automática): ");
            string r = leerLinea("  Ruta del script [" + SCRIPT_PY + "]: ");
            if (!c.empty()) CMD_PYTHON = quitarComillasExternas(c);
            if (!r.empty()) SCRIPT_PY = quitarComillasExternas(r);
            PYTHON_VERIFICADO = false;
            cout << "  Comprobando el módulo de importación...\n";
            if (detectarPython()) cout << "  Módulo de importación listo.\n";
            else cout << "  No se pudo ejecutar el módulo con esa configuración.\n";
            ifstream existe(SCRIPT_PY.c_str());
            cout << (existe ? "  Script encontrado: " : "  ATENCIÓN: no se encuentra el script: ") << SCRIPT_PY << "\n";
        }
        esperarEnter();
    }
}

// =====================================================================
// 17. COLA DE IMPORTACIONES Y PILA DE HISTORIAL
// =====================================================================
void menuCola() {
    while (true) {
        titulo("COLA DE IMPORTACIONES (FIFO)");
        cout << " Pendientes: " << S.importaciones.tam << "\n";
        int k = 1;
        for (Nodo* n = S.importaciones.frente; n != NULL && k <= 15; n = n->sig, k++) {
            Importacion* q = (Importacion*)n->dato;
            cout << "  " << pad(aTexto(k), 4) << pad(q->tipo, 6) << pad(q->codigo, 12)
                 << pad(q->estado, 12) << cortar(q->origen, 60) << "\n";
        }
        if (S.importaciones.tam > 15) cout << "  ... y " << (S.importaciones.tam - 15) << " más\n";
        cout << "\n 1. Encolar una fuente (URL / archivo)\n 2. Editar el origen del primero\n"
                " 3. Quitar el primero de la cola\n 4. Procesar toda la cola\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 4);
        if (op == 0) return;
        if (op == 1) {
            Importacion* q = new Importacion;
            q->tipo = leerLinea("  Tipo (url, html, pdf, csv): ");
            q->origen = leerLinea("  Origen (URL o ruta): ");
            q->estado = "pendiente";
            if (q->tipo.empty() || q->origen.empty()) { delete q; cout << "  Cancelado.\n"; continue; }
            colaEncolar(S.importaciones, q);
            SUCIO = true;
        } else if (op == 2) {
            if (colaVacia(S.importaciones)) { cout << "  La cola está vacía.\n"; continue; }
            Importacion* q = (Importacion*)S.importaciones.frente->dato;
            q->origen = leerCampo("  Nuevo origen", q->origen);
            SUCIO = true;
        } else if (op == 3) {
            if (colaVacia(S.importaciones)) { cout << "  La cola está vacía.\n"; continue; }
            if (confirmar("  ¿Quitar el primero de la cola?")) {
                delete (Importacion*)colaDesencolar(S.importaciones);
                SUCIO = true;
            }
        } else {
            procesarColaConPython();
            esperarEnter();
        }
    }
}

void menuHistorial() {
    while (true) {
        titulo("HISTORIAL DE OPERACIONES (PILA, LIFO)");
        cout << " Operaciones apiladas: " << S.historial.tam << "\n";
        int k = 1;
        for (Nodo* n = S.historial.tope; n != NULL && k <= 15; n = n->sig, k++) {
            Operacion* o = (Operacion*)n->dato;
            cout << "  " << (k == 1 ? "> " : "  ") << pad(aTexto(k), 3) << o->op << " " << o->ent << " " << o->clave << "\n";
        }
        cout << "\n 1. Deshacer la última operación (desapilar)\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 1);
        if (op == 0) return;
        cout << "  " << deshacerUltima(S) << "\n";
        SUCIO = true;
    }
}

// =====================================================================
// 18. ARCHIVO Y MENÚ PRINCIPAL
// =====================================================================
void cargarDatos(const string& ruta) {
    vector<string> avisos;
    string error = cargarTxt(S, ruta, avisos);
    if (!error.empty()) {
        cout << "  " << error << "\n";
        if (error.compare(0, 18, "No se pudo abrir e") == 0)
            cout << "  Ayuda: copie el archivo .txt junto al programa, escriba la ruta completa en\n"
                    "  'Archivo > Cargar datos', o genere los datos con la opción 5 (Importar datos).\n";
        return;
    }
    RUTA_DATOS = ruta;
    SUCIO = false;
    cout << "  Datos cargados: " << S.grupos.tam << " grupos, " << S.investigadores.tam
         << " investigadores, " << S.productos.tam << " productos.\n";
    for (size_t k = 0; k < avisos.size() && k < 10; k++) cout << "  ! " << avisos[k] << "\n";
}

void guardarDatos(const string& ruta) {
    string error = guardarTxt(S, ruta);
    if (!error.empty()) { cout << "  " << error << "\n"; return; }
    RUTA_DATOS = ruta;
    SUCIO = false;
    cout << "  Datos guardados en: " << ruta << "\n";
}

void menuArchivo() {
    while (true) {
        titulo("ARCHIVO (persistencia)");
        cout << " Archivo actual: " << RUTA_DATOS << "\n\n"
                " 1. Cargar datos desde un archivo .txt (generado por este programa o por la versión con interfaz gráfica)\n"
                " 2. Guardar\n 3. Guardar como...\n 4. Vaciar todos los datos\n 0. Volver\n";
        int op = leerEntero(" Opción: ", 0, 4);
        if (op == 0) return;
        if (op == 1) {
            string r = leerLinea("  Ruta del archivo [" + RUTA_DATOS + "]: ");
            cargarDatos(r.empty() ? RUTA_DATOS : r);
        } else if (op == 2) {
            guardarDatos(RUTA_DATOS);
        } else if (op == 3) {
            string r = leerLinea("  Nueva ruta: ");
            if (!r.empty()) guardarDatos(r);
        } else if (confirmar("  ¿Vaciar TODOS los datos de memoria?")) {
            sistemaVaciar(S);
            SUCIO = true;
            cout << "  Datos vaciados.\n";
        }
        esperarEnter();
    }
}

void cambiarVentana() {
    cout << "\n Ventana de observación actual: "
         << (VENTANA_N == 0 ? string("histórico completo") : "últimos " + aTexto(VENTANA_N) + " años") << "\n";
    VENTANA_N = leerEntero(" Años hacia atrás incluyendo el actual (0 = histórico, ej. 2, 5): ", 0, 100);
    cout << "  Ventana actualizada.\n";
}

void menuPrincipal() {
    while (true) {
        titulo("PEA-i  |  Universidad Popular del Cesar");
        cout << " Datos: " << S.grupos.tam << " grupos | " << S.investigadores.tam << " investigadores | "
             << S.productos.tam << " productos | cola: " << S.importaciones.tam << " | historial: "
             << S.historial.tam << (SUCIO ? "   [cambios sin guardar]" : "") << "\n"
             << " Ventana de observación: "
             << (VENTANA_N == 0 ? string("histórico completo") : "últimos " + aTexto(VENTANA_N) + " años") << "\n\n"
                " 1. Grupos\n 2. Investigadores\n 3. Productos\n 4. Estadísticas\n"
                " 5. Importar datos (URL, HTML, PDF, CSV)\n 6. Historial / Deshacer\n"
                " 7. Ventana de observación (años)\n 8. Archivo (cargar / guardar)\n 0. Salir\n";
        // Opción OCULTA 99: gestión de la COLA de importaciones (no se muestra en el menú).
        int op = leerEntero(" Opción: ", 0, 99);
        if (op == 0) {
            if (SUCIO && confirmar(" Hay cambios sin guardar. ¿Guardar en " + RUTA_DATOS + " antes de salir?"))
                guardarDatos(RUTA_DATOS);
            return;
        }
        if (op == 1) menuGrupos();
        else if (op == 2) menuInvestigadores();
        else if (op == 3) menuProductos();
        else if (op == 4) menuEstadisticas();
        else if (op == 5) menuImportar();
        else if (op == 6) menuHistorial();
        else if (op == 7) cambiarVentana();
        else if (op == 8) menuArchivo();
        else if (op == 99) menuCola();
        else cout << "  Opción no válida.\n";
    }
}

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);
#endif
    sistemaIniciar(S);
    cout << "\n PEA-i - Programa Estadístico de Análisis de Investigación (C++)\n"
            " Universidad Popular del Cesar - Estructura de Datos\n";
    if (argc > 1) RUTA_DATOS = argv[1];
    if (confirmar("\n ¿Cargar los datos desde el archivo '" + RUTA_DATOS + "'?"))
        cargarDatos(RUTA_DATOS);
    else
        cout << "  Se inicia sin datos. Use la opción 5 para importar datos.\n";
    menuPrincipal();
    sistemaVaciar(S);
    cout << "\n Hasta pronto.\n";
    return 0;
}
