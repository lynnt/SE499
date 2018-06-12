_Task T {
    void a() {
        //for (int i = 0; i < 100000000000; i++);
        while (1);
    }
    void main() {
        a();
    }
  public:
    T() {}
    T( const char * name, uCluster & x ) : uBaseTask( x ) { setName( name ); }
};

int main() {
    int n = 10;
    T p[n];
    /*
    uProcessor p[3];
    {
    }
    uCluster fred( "fred" );
    uProcessor jane( fred );
    T* p[n];
    for (int i = 0; i < n; i += 1) {
        p[i] = new T("jack", fred);
    }

    for (int i = 0; i < n; i += 1) {
        delete p[i];
    }
    uProcessor p[3];
    {
        T p[3];
        //T jack( "jack", fred );
    }
    */
} // main
