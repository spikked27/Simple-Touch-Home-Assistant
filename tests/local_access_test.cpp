#include "../firmware/simple_touch/local_access.h"
#include <cassert>
int main(){
 using namespace local_access;
 assert(subnet(0xc000020b,0xc000020a,0xffffff00));
 assert(!subnet(0xc000030b,0xc000020a,0xffffff00));
 assert(!subnet(1,0,0));
 auto check=[](bool near,const char* host,const char* origin,const char* ui,bool proxy){
   return allowed(near,host,"192.0.2.10","192.168.4.1","simpletouch-test",origin,ui,proxy);
 };
 assert(check(true,"192.0.2.10","","1",false));
 assert(check(true,"simpletouch-test.local:80","http://simpletouch-test.local:80","1",false));
 assert(check(true,"192.168.4.1","","1",false));
 assert(!check(false,"192.0.2.10","","1",false));
 assert(!check(true,"evil.example","","1",false));
 assert(!check(true,"192.0.2.10","https://evil.example","1",false));
 assert(!check(true,"192.0.2.10","","",false));
 assert(!check(true,"192.0.2.10","","1",true));
 assert(!check(true,"192.0.2.10:8080","","1",false));
}
