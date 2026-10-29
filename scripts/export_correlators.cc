// Safe numbered-file export of current SUNClass correlators through ADAT StorageCorrFunc.
#include "dbtype.h"
#include "hadron/hadron_sun_class_npart_npt_corr.h"
#include "hadron/ensem_filenames.h"
#include "io/superb_kv.h"
#include "io/adat_xmlio.h"
#include <complex>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <vector>
int main(int argc,char**argv) {
  if(argc!=3) {std::cerr<<"Usage: export_correlators INPUT_DB NEW_OUTPUT_DIR\n";return 2;}
  try {
    namespace fs=std::filesystem;
    fs::path output(argv[2]);
    if(fs::exists(output))throw std::runtime_error("Output already exists");
    ADATIO::StorageCorrFunc<Hadron::KeyHadronSUNClassNPartNPtCorr_t> db;
    db.open_for_reading(argv[1]);auto keys=db.keys();
    if(keys.empty())throw std::runtime_error("No correlator keys");
    fs::create_directories(output);
    ADATXML::XMLFileWriter index((output/"index.xml").string());
    ADATXML::push(index,"Exports");
    for(std::size_t i=0;i<keys.size();++i) {
      std::vector<std::vector<std::complex<double>>> values;
      if(db.get(keys[i],values)!=0 || values.empty() || values[0].empty())throw std::runtime_error("Missing/empty correlator");
      std::ostringstream name;name<<"key-"<<std::setfill('0')<<std::setw(6)<<i<<".dat";
      std::ofstream file(output/name.str());
      if(!file)throw std::runtime_error("Cannot open numeric output");
      file<<values.size()<<" "<<values[0].size()<<" 1 0 1\n"<<std::setprecision(17);
      for(const auto& row:values) {
        if(row.size()!=values[0].size())throw std::runtime_error("Inconsistent time shape");
        for(std::size_t t=0;t<row.size();++t)file<<t<<" "<<row[t].real()<<" "<<row[t].imag()<<"\n";
      }
      file.close();if(!file)throw std::runtime_error("Cannot finish numeric output");
      ADATXML::push(index,"elem");
      ADATXML::write(index,"filename",name.str());
      ADATXML::write(index,"standard_filename",Hadron::ensemFileName(keys[i]));
      Hadron::write(index,"Key",keys[i]);
      ADATXML::pop(index);
    }
    ADATXML::pop(index);index.close();
    std::cout<<"Exported "<<keys.size()<<" keys with numbered filenames\n";
  }catch(const std::string&e){std::cerr<<e<<"\n";return 1;}
   catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
