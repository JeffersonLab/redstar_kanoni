// Read the saved single-precision time-slice MOD gauge without regenerating it.
#include "chromabase.h"
#include "qdp_map_obj_disk.h"
#include "qdp_disk_map_slice.h"
#include "util/gauge/key_timeslice_gauge.h"
#include "io/gauge_io.h"
#include <filesystem>
#include <iostream>
#include <sstream>
using namespace Chroma;
int main(int argc,char**argv) {
 QDP_initialize(&argc,&argv);
 int result=0;
 try {
  if(argc!=3)throw std::runtime_error("usage: mod_gauge_to_qio INPUT.mod NEW_OUTPUT.lime");
  const std::string input=argv[1],output=argv[2];
  if(std::filesystem::exists(output))throw std::runtime_error("Output exists; refusing overwrite");
  QDP::MapObjectDisk<KeyTimeSliceGauge_t,TimeSliceIO<LatticeColorMatrixF>> db;
  db.open(input,std::ios_base::in);std::string metadata;db.getUserdata(metadata);
  std::istringstream stream(metadata);XMLReader xml(stream);
  std::string id;read(xml,"/MODMetaData/id",id);
  if(id!="gaugeFieldTimeSlice")throw std::runtime_error("Not a time-slice gauge MOD");
  int precision,decay;read(xml,"/MODMetaData/ProgramInfo/code_version/basePrecision",precision);read(xml,"/MODMetaData/decay_dir",decay);
  if(precision!=32 || decay!=3)throw std::runtime_error("This importer requires a 32-bit temporal-slice gauge MOD");
  multi1d<int> nrow;read(xml,"/MODMetaData/lattSize",nrow);Layout::setLattSize(nrow);Layout::create();
  multi1d<LatticeColorMatrixF> source(Nd);
  multi1d<LatticeColorMatrix> promoted(Nd);
  for(int mu=0;mu<Nd;++mu) {
   source[mu]=zero;
   for(int t=0;t<nrow[3];++t) {
    KeyTimeSliceGauge_t key;key.t_slice=t;key.dir=mu;
    TimeSliceIO<LatticeColorMatrixF> slice(source[mu],t);
    if(db.get(key,slice)!=0)throw std::runtime_error("Missing gauge direction/time slice");
   }
   promoted[mu]=source[mu];
  }
  db.close();
  XMLBufferWriter file_xml,record_xml;
  push(file_xml,"MatchedMODGauge");write(file_xml,"source",input);write(file_xml,"source_precision_bits",precision);pop(file_xml);
  record_xml<<xml;
  writeGauge(file_xml,record_xml,promoted,output,QDPIO_SINGLEFILE,QDPIO_SERIAL);
  multi1d<LatticeColorMatrix> restored(Nd);XMLReader f,r;
  readGauge(f,r,restored,output,QDPIO_SERIAL);
  Double error=zero;
  for(int mu=0;mu<Nd;++mu)error+=norm2(restored[mu]-promoted[mu]);
  if(toDouble(error)!=0)throw std::runtime_error("Gauge roundtrip changed saved link values");
  QDPIO::cout<<"PASS: "<<Nd*nrow[3]<<" MOD gauge slices; exact float-to-native promotion and QIO roundtrip; squared error="<<error<<std::endl;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;result=1;}
 catch(const std::string& e){std::cerr<<e<<std::endl;result=1;}
 QDP_finalize();return result;
}
