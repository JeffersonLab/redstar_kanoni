#include "io/superb_aux.h"
#include <iostream>
#include <limits>
#include <cmath>
#include <functional>
using T=std::complex<double>;
template<size_t N>void validate(const char*file,const std::vector<char>&metadata,const std::vector<superbblas::IndexType>&dimensions){
 auto options=SB::getOptionsFromXML(std::string(metadata.begin(),metadata.end()));auto order=SB::getOption<std::string>(*options,"DBMetaData/tensorOrder");if(order.size()!=N)throw std::runtime_error("Invalid tensor order");
 superbblas::Storage_handle h;superbblas::open_storage<N,T>(file,false,&h);
 try{
  superbblas::check_storage<N,T>(h);
  superbblas::Coor<N>dim{};for(size_t a=0;a<N;++a){dim[a]=dimensions[a];if(dim[a]<=0)throw std::runtime_error("Empty dimension");}
  std::vector<superbblas::PartitionItem<N>>blocks;superbblas::get_blocks<N,N,T>(h,order.c_str(),order.c_str(),superbblas::Coor<N>{},dim,blocks,superbblas::FastToSlow);if(blocks.empty())throw std::runtime_error("No stored blocks");
  size_t values=0;double maximum=0;auto cpu=superbblas::createCpuContext();
  for(const auto&block:blocks){auto chunk=block[1];auto volume=[&](){size_t v=1;for(auto x:chunk)v*=x;return v;};while(volume()>65536){size_t axis=std::max_element(chunk.begin(),chunk.end())-chunk.begin();chunk[axis]=(chunk[axis]+1)/2;}
   superbblas::Coor<N>offset{};bool more=true;while(more){superbblas::Coor<N>from{},size{},zero{};size_t n=1;for(size_t a=0;a<N;++a){from[a]=block[0][a]+offset[a];size[a]=std::min(chunk[a],block[1][a]-offset[a]);n*=size[a];}
    std::vector<T>data(n,T(std::numeric_limits<double>::quiet_NaN(),0));T*ptr=data.data();superbblas::PartitionItem<N>part{zero,size};
#if SUPERBBLAS_VERSION < 2
    superbblas::load<N,N,T,T>(T(1),h,order.c_str(),from,size,&part,1,order.c_str(),zero,&ptr,&cpu,superbblas::FastToSlow,superbblas::Copy);
#else
    superbblas::load<N,N,T,T>(T(1),h,order.c_str(),from,size,&part,1,order.c_str(),zero,size,&ptr,&cpu,superbblas::FastToSlow,superbblas::Copy);
#endif
    for(auto z:data){if(!std::isfinite(z.real())||!std::isfinite(z.imag()))throw std::runtime_error("Nonfinite stored value");maximum=std::max(maximum,std::abs(z));}values+=n;
    size_t a=0;for(;a<N;++a){offset[a]+=chunk[a];if(offset[a]<block[1][a])break;offset[a]=0;}more=a<N;
   }
  }
  std::cout<<"{\"status\":\"passed\",\"rank\":"<<N<<",\"stored_blocks\":"<<blocks.size()<<",\"finite_complex_values\":"<<values<<",\"max_abs\":"<<maximum<<",\"checksums\":\"passed\"}\n";
  superbblas::close_storage<N,T>(h);
 }catch(...){superbblas::close_storage<N,T>(h);throw;}
}
int main(int argc,char**argv){try{if(argc!=2)throw std::runtime_error("usage: validate_superb_tensor FILE");std::vector<char>meta;std::vector<superbblas::IndexType>dims;superbblas::values_datatype dtype;superbblas::read_storage_header(argv[1],superbblas::FastToSlow,dtype,meta,dims);if(dtype!=superbblas::detail::get_values_datatype<T>())throw std::runtime_error("Expected complex<double> tensor");switch(dims.size()){case 4:validate<4>(argv[1],meta,dims);break;case 5:validate<5>(argv[1],meta,dims);break;case 7:validate<7>(argv[1],meta,dims);break;case 8:validate<8>(argv[1],meta,dims);break;case 10:validate<10>(argv[1],meta,dims);break;default:throw std::runtime_error("Unsupported tensor rank");}return 0;}catch(std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
