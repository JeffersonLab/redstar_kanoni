#include <mpi.h>
#include <omp.h>
#include <qdp.h>
#include <qmp.h>

#include <fstream>
#include <stdexcept>
#include <string>

#ifndef ARCH_PARSCALAR
#error "run_chroma MPI requires QDP parscalar"
#endif

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const int expected = std::stoi(argv[1]);
  const int requested_threads = std::stoi(argv[2]);
  QDP::QDP_initialize(&argc, &argv);
  try {
    int initialized = 0;
    MPI_Initialized(&initialized);
    if (!initialized)
      throw std::runtime_error("QMP did not initialize MPI");
    int rank = -1, size = 0, thread_level = -1;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);
    MPI_Query_thread(&thread_level);
    if (size != expected || QMP_get_number_of_nodes() != size ||
        QMP_get_node_number() != rank)
      throw std::runtime_error("QMP and MPI world ranks disagree");
    if (requested_threads > 1 && thread_level < MPI_THREAD_FUNNELED)
      throw std::runtime_error("MPI thread support is below FUNNELED");
    QDP::multi1d<int> lattice(4);
    lattice[0] = lattice[1] = lattice[2] = 4;
    lattice[3] = 16;
    QDP::Layout::setLattSize(lattice);
    QDP::Layout::create();
    QDP::LatticeReal ones = QDP::Real(1);
    const double total = QDP::toDouble(QDP::sum(ones));
    if (total != 1024 || QDP::Layout::sitesOnNode() * size != 1024)
      throw std::runtime_error("QDP lattice distribution is inconsistent");
    int threads = 0;
#pragma omp parallel
    {
#pragma omp atomic
      ++threads;
    }
    if (threads != requested_threads)
      throw std::runtime_error("Actual OpenMP team differs from --threads");
    std::ofstream report("mpi-runtime-rank-" + std::to_string(rank) + ".json");
    report << "{\"rank\":" << rank << ",\"mpi_ranks\":" << size
           << ",\"qmp_nodes\":" << QMP_get_number_of_nodes()
           << ",\"qmp_rank\":" << QMP_get_node_number()
           << ",\"global_sum\":" << total
           << ",\"local_volume\":" << QDP::Layout::sitesOnNode()
           << ",\"openmp_threads\":" << threads
           << ",\"mpi_thread_level\":" << thread_level << "}\n";
    if (!report)
      throw std::runtime_error("Cannot write MPI runtime report");
  } catch (const std::exception &error) {
    QDP::QDPIO::cerr << error.what() << '\n';
    QDP::QDP_abort(1);
  } catch (const std::string &error) {
    QDP::QDPIO::cerr << error << '\n';
    QDP::QDP_abort(1);
  }
  QDP::QDP_finalize();
  return 0;
}
