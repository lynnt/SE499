#include <string>

_Task T {
    std::string name;
    void a(int param) {
        int x = 3;
        std::string y = "example";
        while(1);
    }
    void main() {
        a(5);
    }
  public:
    T( const int tid) {
        name = "T" + std::to_string(tid);
        setName( name.c_str() );
    }
};

const int n = 10;
T* tasks[n];
T* global_ptr_S;

int main() {
    uProcessor p[3];
    for (int i = 0; i < n; i += 1) {
        tasks[i] = new T(i);
        global_ptr_S = tasks[0];
    }

    for (int i = 0; i < n; i += 1) {
        delete tasks[i];
    }
} // main
