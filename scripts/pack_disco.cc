#include "io/disco_superb.h"
#include <set>
#include <fstream>
#include <iostream>
int main(int argc,char**argv){try{
 if(argc<3)throw std::runtime_error("usage: pack_disco OUTPUT INPUT... (new output; no overwriting)");
 if(std::ifstream(argv[1]).good())throw std::runtime_error("output already exists");
 ADATIO::StorageDisco input;input.open(std::vector<std::string>(argv+2,argv+argc));
 std::vector<Hadron::KeyTwoQuarkDiscoOperator_t> keys;input.keys(keys);
 if(keys.empty()||std::set<Hadron::KeyTwoQuarkDiscoOperator_t>(keys.begin(),keys.end()).size()!=keys.size())throw std::runtime_error("empty/overlapping input keys");
 auto options=SB::getOptionsFromXML(input.meta.at(0));auto lattice=SB::getOption<std::vector<int>>(*options,"DBMetaData/lattSize");
 std::set<std::string> masses;std::set<std::vector<int>>paths;std::set<std::array<int,3>>moms;
 for(const auto&k:keys){masses.insert(k.mass_label);paths.insert(k.disp);moms.insert({k.mom[0],k.mom[1],k.mom[2]});}
 ADATIO::StorageDisco output;output.create_mass_collection(argv[1],lattice,{masses.begin(),masses.end()},{paths.begin(),paths.end()},{moms.begin(),moms.end()},input.meta);
 for(const auto&k:keys){Hadron::ValTwoQuarkDiscoOperator_t v;if(input.get(k,v)||output.insert(k,v))throw std::runtime_error("packing a key failed");}output.close();
 output.open({argv[1]});std::vector<Hadron::KeyTwoQuarkDiscoOperator_t> packed;output.keys(packed);if(packed.size()!=keys.size())throw std::runtime_error("packed key coverage mismatch");
 size_t values=0;for(const auto&k:keys){Hadron::ValTwoQuarkDiscoOperator_t a,b;if(input.get(k,a)||output.get(k,b)||a.op!=b.op)throw std::runtime_error("packed values differ");values+=a.op.size();}
 std::cout<<"keys="<<keys.size()<<" finite_values="<<values<<" exact_source_readback=passed\n";return 0;
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}}
