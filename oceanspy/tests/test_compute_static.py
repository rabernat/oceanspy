import pytest
import xarray as xr
import copy
from .datasets import oceandatasets, MITgcmVarDims
from oceanspy.compute import *
from oceanspy import utils
from numpy.random import rand, uniform
from numpy.testing import assert_array_equal, assert_allclose
import numpy as np

# Add variables
od_in = copy.copy(oceandatasets['MITgcm_rect_nc'])

# Add random values
varNeeded = ['Temp', 'S', 
             'HFacC', 'HFacW', 'HFacS',
             'rAz', 'rA',
             'dyC', 'dxC', 'dxF', 'dyF', 'dxG', 'dyG', 'dxV', 'dyU',
             'drF', 
             'U', 'V', 'W',
             'fCoriG',
             'AngleCS', 'AngleSN']

ds_dict = {}
for name, dimList in MITgcmVarDims.items():
    if name not in varNeeded: continue
    dimSize = [len(od_in.dataset[dim]) for dim in dimList]
    if name in ['AngleCS', 'AngleSN']:
        ds_dict[name] = xr.DataArray(np.ones(dimSize), dims=dimList)
    else:
        ds_dict[name] = xr.DataArray(rand(*dimSize), dims=dimList)
ds_in = xr.Dataset(ds_dict)
od_in = od_in.merge_into_oceandataset(ds_in)    



def test_potential_density_anomaly():
    
    # Compute Sigma0
    ds_out = potential_density_anomaly(od_in)
    assert ds_out['Sigma0'].attrs['units']     == 'kg/m^3'
    assert ds_out['Sigma0'].attrs['long_name'] == 'potential density anomaly'
    check_params(ds_out, 'Sigma0', ['eq_state'])
    
    # Check values
    Sigma0 = eval("utils.dens{}(od_in.dataset['S'].values, od_in.dataset['Temp'].values, 0)".format(od_in.parameters['eq_state']))
    assert_array_equal(ds_out['Sigma0'].values+1000, Sigma0)
    
    # Test shortcut
    od_out=od_in.compute.potential_density_anomaly()
    ds_out_IN_od_out(ds_out, od_out)
    
def test_Brunt_Vaisala_frequency():
    
    # Compute N2
    ds_out = Brunt_Vaisala_frequency(od_in)
    assert ds_out['N2'].attrs['units']     == 's^-2'
    assert ds_out['N2'].attrs['long_name'] == 'Brunt-Väisälä Frequency'
    check_params(ds_out, 'N2', ['g', 'rho0'])
    
    # Check values
    dSigma0_dZ = gradient(od_in, 'Sigma0', 'Z')
    dSigma0_dZ = dSigma0_dZ['dSigma0_dZ']
    assert_allclose(-dSigma0_dZ.values*od_in.parameters['g']/od_in.parameters['rho0'], ds_out['N2'].values)
    
    # Test shortcut
    od_out=od_in.compute.Brunt_Vaisala_frequency()
    ds_out_IN_od_out(ds_out, od_out)
    

def test_vertical_relative_vorticity():
    
    # Compute momVort3
    ds_out = vertical_relative_vorticity(od_in)
    assert ds_out['momVort3'].attrs['units']     == 's^-1'
    assert ds_out['momVort3'].attrs['long_name'] == 'vertical component of relative vorticity'
    
    # Check values
    zeta = curl(od_in, iName='U',  jName='V',)
    zeta = zeta['dV_dX-dU_dY'] 
    assert_allclose(zeta.values, ds_out['momVort3'].values)
    
    # Test shortcut
    od_out=od_in.compute.vertical_relative_vorticity()
    ds_out_IN_od_out(ds_out, od_out)
    
def test_relative_vorticity():
    
    # Compute momVort1, momVort2, momVort3
    ds_out = relative_vorticity(od_in)
    varName = 'momVort'
    for i in range(3): 
        assert ds_out[varName+str(i+1)].attrs['units']     == 's^-1'
        assert ds_out[varName+str(i+1)].attrs['long_name'] == '{}-component of relative vorticity'.format(chr(105+i))
    
    # Check values
    vort = curl(od_in, iName='U',  jName='V', kName='W')
    for i, curlName in enumerate(['dW_dY-dV_dZ', 'dU_dZ-dW_dX', 'dV_dX-dU_dY']):
        assert_allclose(vort[curlName].values, ds_out[varName+str(i+1)].values)

    # Test shortcut
    od_out=od_in.compute.relative_vorticity()
    ds_out_IN_od_out(ds_out, od_out)
    
    
def test_kinetic_energy():
    
    # Compute KE
    ds_out = kinetic_energy(od_in)
    assert ds_out['KE'].attrs['units']     == 'm^2 s^-2'
    assert ds_out['KE'].attrs['long_name'] == 'kinetic energy'
    check_params(ds_out, 'KE', ['eps_nh'])
    
    # Check values
    # TODO: add non-hydrostatic test
    U = (od_in.dataset['U'].values[:,:,:,1:] + od_in.dataset['U'].values[:,:,:,:-1])/2
    V = (od_in.dataset['V'].values[:,:,1:,:] + od_in.dataset['V'].values[:,:,:-1,:])/2
    KE = (U**2+V**2)/2
    assert_allclose(KE, ds_out['KE'].values)
    
    # Test shortcut
    od_out=od_in.compute.kinetic_energy()
    ds_out_IN_od_out(ds_out, od_out)
    
def test_eddy_kinetic_energy():
    
    # Compute KE
    ds_out = eddy_kinetic_energy(od_in)
    assert ds_out['EKE'].attrs['units']     == 'm^2 s^-2'
    assert ds_out['EKE'].attrs['long_name'] == 'eddy kinetic energy'
    check_params(ds_out, 'EKE', ['eps_nh'])
    
    # Check values
    # TODO: add non-hydrostatic test
    U = od_in.dataset['U'] - od_in.dataset['U'].mean('time')
    V = od_in.dataset['V'] - od_in.dataset['V'].mean('time')
    U = (U.values[:,:,:,1:] + U.values[:,:,:,:-1])/2
    V = (V.values[:,:,1:,:] + V.values[:,:,:-1,:])/2
    EKE = (U**2+V**2)/2
    assert_allclose(EKE, ds_out['EKE'].values)
    
    # Test shortcut
    od_out=od_in.compute.eddy_kinetic_energy()
    ds_out_IN_od_out(ds_out, od_out)
    
    
def test_horizontal_divergence_velocity():
    
    # Compute hor_div_vel
    ds_out = horizontal_divergence_velocity(od_in)
    assert ds_out['hor_div_vel'].attrs['units']     == 'm s^-2'
    assert ds_out['hor_div_vel'].attrs['long_name'] == 'horizontal divergence of the velocity field'
    
    # Check values
    hor_div = divergence(od_in, iName='U',  jName='V')
    hor_div = hor_div['dU_dX'] + hor_div['dV_dY']
    assert_allclose(hor_div.values, ds_out['hor_div_vel'].values)
    
    # Test shortcut
    od_out=od_in.compute.horizontal_divergence_velocity()
    ds_out_IN_od_out(ds_out, od_out)
    
    
def test_shear_strain():
    
    # Compute s_strain
    ds_out = shear_strain(od_in)
    assert ds_out['s_strain'].attrs['units']     == 's^-1'
    assert ds_out['s_strain'].attrs['long_name'] == 'shear component of strain'
    
    # Does it make sense to test this just rewriting the same equation in compute?
    # I don't think so... Here I'm just testing that it works....
    
    # Test shortcut
    od_out=od_in.compute.shear_strain()
    ds_out_IN_od_out(ds_out, od_out)

def test_normal_strain():
    
    # Compute n_strain
    ds_out = normal_strain(od_in)
    assert ds_out['n_strain'].attrs['units']     == 's^-1'
    assert ds_out['n_strain'].attrs['long_name'] == 'normal component of strain'
    
    # Check values
    divs = divergence(od_in, iName='U', jName='V')
    assert_allclose((divs['dU_dX']-divs['dV_dY']).values, ds_out['n_strain'].values)
    
    # Test shortcut
    od_out=od_in.compute.normal_strain()
    ds_out_IN_od_out(ds_out, od_out)

@pytest.mark.parametrize("full", [False, True])    
def test_Ertel_potential_vorticity(full):
    
    # Compute Ertel_PV
    ds_out = Ertel_potential_vorticity(od_in, full)
    assert ds_out['Ertel_PV'].attrs['units']     == 'm^-1 s^-1'
    assert ds_out['Ertel_PV'].attrs['long_name'] == 'Ertel potential vorticity'
    
    # Does it make sense to test this just rewriting the same equation in compute?
    # I don't think so... Here I'm just testing that it works....
    
    # Test shortcut
    od_out=od_in.compute.Ertel_potential_vorticity(full=full)
    ds_out_IN_od_out(ds_out, od_out)    
    
def test_mooring_horizontal_volume_transport():
    
    # Error if it's not a mooring
    with pytest.raises(ValueError) as e:
        ds_out = mooring_horizontal_volume_transport(od_in)
    assert str(e.value) == "oceadatasets must be subsampled using `subsample.mooring_array`"
    
    # Get random coords
    X = od_in.dataset['XC'].stack(XY=('X', 'Y')).values
    Y = od_in.dataset['YC'].stack(XY=('X', 'Y')).values
    inds = np.random.choice(len(X), 3, replace=False)
    Xmoor = X[inds]
    Ymoor = Y[inds]
    
    # Run mooring
    od_moor = od_in.subsample.mooring_array(Xmoor=Xmoor, Ymoor=Ymoor)
    
    # Compute transport
    ds_out = mooring_horizontal_volume_transport(od_moor)
    assert 'path' in ds_out.dims
    
    # Max 2 velocities per grid cell
    sum_dirs = (np.fabs(ds_out['dir_Utransport'].sum('path'))+np.fabs(ds_out['dir_Vtransport'].sum('path'))).values
    assert np.all(np.logical_and(sum_dirs>=0,sum_dirs<=2))
    assert_allclose((ds_out['Utransport']+ds_out['Vtransport']).values, ds_out['transport'].values)
    
    # Test shortcut
    od_out=od_moor.compute.mooring_horizontal_volume_transport()
    ds_out_IN_od_out(ds_out, od_out)
    
def test_survey_aligned_velocities():
    
    # Error if it's not a survey
    with pytest.raises(ValueError) as e:
        ds_out = survey_aligned_velocities(od_in)
    assert str(e.value) == "oceadatasets must be subsampled using `subsample.survey_stations`"

    # Get random coords
    X = od_in.dataset['XC'].stack(XY=('X', 'Y')).values
    Y = od_in.dataset['YC'].stack(XY=('X', 'Y')).values
    Xsurv = X[[0, -1]]
    Ysurv = Y[[0, -1]]
    
    with pytest.warns(UserWarning):
        # Run survey
        od_surv = od_in.subsample.survey_stations(Xsurv=Xsurv, Ysurv=Ysurv, varList=['U', 'V'])

        # Align velocities
        ds_out = survey_aligned_velocities(od_surv)
    
    vel_surv = np.sqrt(od_surv.dataset['U']**2 + od_surv.dataset['V']**2)
    vel_alig = np.sqrt(ds_out['tan_Vel']**2 + ds_out['ort_Vel']**2)
    assert_allclose(vel_surv.values, vel_alig.values)
    
    # Meridional
    Xsurv = [np.mean(X), np.mean(X)]
    Ysurv = Y[[0, -1]]
    
    with pytest.warns(UserWarning):
        # Run survey
        od_surv = od_in.subsample.survey_stations(Xsurv=Xsurv, Ysurv=Ysurv, varList=['U', 'V'])

        # Align velocities
        ds_out = survey_aligned_velocities(od_surv)
    assert np.all(np.round(ds_out['rot_ang_Vel'].values)==90) 
    # TODO: looks like this doesn't need round (exactly 90°)
    #       Keep round for consistency with the case below
    
    # Zonal
    Xsurv = X[[0, -1]]
    Ysurv = [np.mean(Y), np.mean(Y)]
    
    with pytest.warns(UserWarning):
        # Run survey
        od_surv = od_in.subsample.survey_stations(Xsurv=Xsurv, Ysurv=Ysurv, varList=['U', 'V'])

        # Align velocities
        ds_out = survey_aligned_velocities(od_surv)
    assert np.all(np.round(ds_out['rot_ang_Vel'].values)==0) 
    # TODO: why do I need to round? Shouldn't it be exactly zero?
    
    # Test shortcut
    with pytest.warns(UserWarning):
        od_out=od_surv.compute.survey_aligned_velocities()
    ds_out_IN_od_out(ds_out, od_out)

def test_geographical_aligned_velocities():
    
    # Compute KE
    ds_out = geographical_aligned_velocities(od_in)
    assert ds_out['U_zonal'].attrs['long_name'] == 'zonal velocity' 
    assert ds_out['U_zonal'].attrs['direction'] == 'positive: eastwards'
    assert ds_out['V_merid'].attrs['long_name'] == 'meridional velocity' 
    assert ds_out['V_merid'].attrs['direction'] == 'positive: northwards'
    
    # Check values
    # TODO: Add check for velocity values (similar to survey aligned)
    #       This function was implemented by Renske, maybe she has something ready
    
    # Test shortcut
    od_out=od_in.compute.geographical_aligned_velocities()
    ds_out_IN_od_out(ds_out, od_out)
    
def check_params(ds, varName, params):
    for par in params:
        assert par in ds[varName].attrs['OceanSpy_parameters']
    
def ds_out_IN_od_out(ds_out, od_out):
    for var in ds_out.data_vars: 
        assert_array_equal(od_out.dataset[var].values, ds_out[var].values)
        
