#
# Parameter file for make_redstar_irrep_xml.pl
# CT, 2011-05-19
#

sub params
{
  $flav_1 = "pion";
  $spin_1 = "0";
  $parity_1 = -1;
#  $gparity_1 = -1;
#  $opname_1 = "proj0";
  $opname_1 = "pionxD0_J0__J0";
  
  $flav_2 = "pion";
  $spin_2 = "0";
  $parity_2 = -1;
#  $gparity_2 = -1;
#  $opname_2 = "proj0";
  $opname_2 = "pionxD0_J0__J0";
  
  $smearedP = "true";
  $creation_op = "false";
  $target_G_parity = -1;
  $target_row = 1;
  $target_twoI = 0;
  $target_twoI_z = 0;
  @target_moms = ("0 0 0", "1 0 0", "1 1 0", "1 1 1");
  $one_order = "false";

  $mom2_max = 2;
  
  $op_prefix = "I2,iz0,";
  $op_suffix = "";
}


# Needed for "require" statement
1;

