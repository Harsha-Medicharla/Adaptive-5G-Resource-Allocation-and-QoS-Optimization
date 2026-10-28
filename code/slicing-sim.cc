/*
 * slicing-sim.cc
 * Adaptive 5G Resource Allocation and QoS Optimization (IT365)
 * Midsem version: rate-based network slicing with a STATIC allocation baseline.
 *
 * Topology (uplink, UEs -> base station):
 *
 *   eMBB UEs  --100Mbps--> GW_eMBB  --[slice pipe, R_eMBB ]--+
 *   URLLC UEs --100Mbps--> GW_URLLC --[slice pipe, R_URLLC]--+--> BS (sink)
 *   mMTC devs --100Mbps--> GW_mMTC  --[slice pipe, R_mMTC ]--+
 *
 * Resource model (documented abstraction, NOT physical PRBs):
 *   100 resource units == 20 Mbps of shared capacity, 1 unit == 0.2 Mbps.
 *   A slice holding u units gets a dedicated pipe of rate u * 0.2 Mbps.
 *   ApplyAllocation() changes the pipe rates at run time; the post-midsem
 *   RL agent will call exactly this function.
 *
 * Queueing: each slice pipe has an explicit FIFO queue disc (default 100 packets)
 *   and a 1-packet device queue. No hidden default scheduler.
 *
 * Build/run inside ns-3:   cp slicing-sim.cc scratch/ && ./ns3 run "slicing-sim --run=1"
 */

#include "ns3/applications-module.h"
#include "ns3/ai-module.h"
#include "ns3/core-module.h"
#include "ns3/internet-module.h"
#include "ns3/network-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/traffic-control-module.h"

#include <algorithm>
#include <array>
#include <cstdlib>
#include <fstream>
#include <map>
#include <numeric>
#include <sstream>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SlicingSim");
#define STDOUT(x) (std::cout << x << std::endl)

// ===========================================================================
// 1. CONFIGURATION (edit here)
// ===========================================================================
enum Slice { EMBB = 0, URLLC = 1, MMTC = 2, NSLICES = 3 };
static const char* SLICE_NAME[NSLICES] = {"eMBB", "URLLC", "mMTC"};

struct SimConfig
{
    // resource pool
    double totalCapacityMbps = 20.0;
    int    totalUnits        = 100;
    std::array<int, NSLICES> staticAlloc = {50, 30, 20};

    // devices per slice
    uint32_t nEmbb  = 3;
    uint32_t nUrllc = 3;
    uint32_t nMmtc  = 60;   // max mMTC devices; phases activate a subset

    // packet sizes (UDP payload, bytes, includes 12 B SeqTs header)
    uint32_t pktEmbb  = 1200;
    uint32_t pktUrllc = 200;
    uint32_t pktMmtc  = 64;

    // per mMTC device: Poisson packets, mean rate
    double mmtcPktPerSec = 100.0;

    // links
    std::string accessRate  = "100Mbps";
    std::string accessDelay = "0.1ms";
    std::string pipeDelay   = "1ms";
    uint32_t    pipeQueuePkts = 100;

    // QoS / measurement
    double urllcTargetMs = 10.0;    // simulation latency budget (NOT 3GPP 1 ms air-interface)
    double mmtcServedPdr = 0.9;     // device "served" in a bin if PDR >= this
    double binS          = 0.1;     // measurement interval
    double duration      = 50.0;
    double drain         = 1.0;     // extra time to let queues empty

    uint32_t run = 1;
    std::string outPrefix = "run1";
};

// Traffic phases: offered PAYLOAD load per slice (eMBB, URLLC in Mbps total;
// mMTC as number of active devices).
struct Phase
{
    double start;
    double embbMbps;
    double urllcMbps;
    uint32_t mmtcDevices;
    std::string label;
};

static std::vector<Phase> MakeScenario()
{
    return {
        {0.0,  6.0, 2.0, 30, "Normal"},
        {10.0, 14.0, 2.0, 30, "eMBB burst"},
        {20.0, 14.0, 5.0, 30, "eMBB + URLLC high"},
        {30.0, 6.0, 9.0, 15, "URLLC very high"},
        {40.0, 9.0, 2.0, 60, "mMTC surge"},
    };
}

static const uint32_t WIRE_OVERHEAD = 30; // IPv4 20 + UDP 8 + PPP 2 bytes

// ===========================================================================
// 2. TRAFFIC SOURCE APPLICATION (CBR or Poisson, rate changeable at run time)
// ===========================================================================
struct Stats; // forward
static void OnTx(int slice, uint32_t dev, Time t);

class SliceSource : public Application
{
  public:
    void Setup(Address peer, uint32_t pktSize, double rateMbps, bool poisson,
               int slice, uint32_t devId, int64_t stream)
    {
        m_peer = peer; m_pktSize = pktSize; m_rateMbps = rateMbps;
        m_poisson = poisson; m_slice = slice; m_dev = devId;
        m_exp = CreateObject<ExponentialRandomVariable>();
        m_exp->SetStream(stream);
        m_uni = CreateObject<UniformRandomVariable>();
        m_uni->SetStream(stream + 1);
    }

    void SetRate(double rateMbps)
    {
        m_rateMbps = rateMbps;
        Reschedule();
    }

    void SetActive(bool on)
    {
        m_active = on;
        Reschedule();
    }

  private:
    void StartApplication() override
    {
        m_socket = Socket::CreateSocket(GetNode(), UdpSocketFactory::GetTypeId());
        m_socket->Bind();
        m_socket->Connect(m_peer);
        m_running = true;
        Reschedule(true);
    }

    void StopApplication() override
    {
        m_running = false;
        Simulator::Cancel(m_event);
        if (m_socket) m_socket->Close();
    }

    Time NextGap()
    {
        double meanS = (m_pktSize * 8.0) / (m_rateMbps * 1e6);
        return Seconds(m_poisson ? m_exp->GetValue(meanS, 0) : meanS);
    }

    void Reschedule(bool randomOffset = false)
    {
        Simulator::Cancel(m_event);
        if (!m_running || !m_active || m_rateMbps <= 0) return;
        Time gap = NextGap();
        if (randomOffset) gap = Seconds(m_uni->GetValue(0, gap.GetSeconds()));
        m_event = Simulator::Schedule(gap, &SliceSource::Send, this);
    }

    void Send()
    {
        SeqTsHeader h;
        h.SetSeq(m_seq++);
        Ptr<Packet> p = Create<Packet>(m_pktSize - h.GetSerializedSize());
        p->AddHeader(h);
        m_socket->Send(p);
        OnTx(m_slice, m_dev, Simulator::Now());
        m_event = Simulator::Schedule(NextGap(), &SliceSource::Send, this);
    }

    Ptr<Socket> m_socket;
    Address m_peer;
    uint32_t m_pktSize = 0;
    double m_rateMbps = 0;
    bool m_poisson = false;
    bool m_active = true;
    bool m_running = false;
    int m_slice = 0;
    uint32_t m_dev = 0;
    uint32_t m_seq = 0;
    EventId m_event;
    Ptr<ExponentialRandomVariable> m_exp;
    Ptr<UniformRandomVariable> m_uni;
};

// ===========================================================================
// 3. MEASUREMENT (per 100 ms bin, per slice)
// ===========================================================================
struct Bin
{
    uint64_t tx = 0;            // packets sent in this bin
    uint64_t rxOfTx = 0;        // of those, delivered (any time)  -> loss
    uint64_t rx = 0;            // packets received in this bin
    uint64_t rxBytes = 0;       // payload bytes received in this bin
    std::vector<double> delayMs;
};

struct Stats
{
    SimConfig cfg;
    int nBins = 0;
    std::array<std::vector<Bin>, NSLICES> bins;
    // mMTC per-device per-bin tx / delivered (by tx bin)
    std::vector<std::vector<uint32_t>> mmtcTx, mmtcOk;
    std::array<int, NSLICES> alloc = {0, 0, 0};
    std::vector<std::array<int, NSLICES>> allocLog;     // per bin
    std::vector<std::array<double, NSLICES>> demandLog; // offered payload Mbps per bin
    std::array<double, NSLICES> demand = {0, 0, 0};
    std::map<uint32_t, std::pair<int, uint32_t>> addrToDev; // ipv4 -> (slice, dev)
};
static Stats g;

static int BinOf(Time t)
{
    int b = int(t.GetSeconds() / g.cfg.binS);
    return std::min(std::max(b, 0), g.nBins - 1);
}

static void OnTx(int slice, uint32_t dev, Time t)
{
    int b = BinOf(t);
    g.bins[slice][b].tx++;
    if (slice == MMTC) g.mmtcTx[dev][b]++;
}

static void OnRx(Ptr<Socket> sock)
{
    Address from;
    Ptr<Packet> p;
    while ((p = sock->RecvFrom(from)))
    {
        SeqTsHeader h;
        p->RemoveHeader(h);
        Time now = Simulator::Now();
        Ipv4Address src = InetSocketAddress::ConvertFrom(from).GetIpv4();
        auto it = g.addrToDev.find(src.Get());
        if (it == g.addrToDev.end()) continue;
        int s = it->second.first;
        uint32_t dev = it->second.second;

        int rb = BinOf(now);
        int tb = BinOf(h.GetTs());
        Bin& r = g.bins[s][rb];
        r.rx++;
        r.rxBytes += p->GetSize() + h.GetSerializedSize();
        r.delayMs.push_back((now - h.GetTs()).GetSeconds() * 1000.0);
        g.bins[s][tb].rxOfTx++;
        if (s == MMTC) g.mmtcOk[dev][tb]++;
    }
}

// Records the allocation/demand in force at the middle of each bin
static void LogBin(int b)
{
    if (b >= (int)g.allocLog.size()) return;
    g.allocLog[b] = g.alloc;
    g.demandLog[b] = g.demand;
    Simulator::Schedule(Seconds(g.cfg.binS), &LogBin, b + 1);
}

// ===========================================================================
// 4. RESOURCE ALLOCATION (the knob the RL agent will turn after midsem)
// ===========================================================================
static std::array<Ptr<PointToPointNetDevice>, NSLICES> g_pipeTx; // GW side
static std::array<Ptr<PointToPointNetDevice>, NSLICES> g_pipeRx; // BS side

static void ApplyAllocation(std::array<int, NSLICES> units)
{
    NS_ABORT_MSG_IF(units[0] + units[1] + units[2] != g.cfg.totalUnits,
                    "allocation must sum to total units");
    double perUnitBps = g.cfg.totalCapacityMbps * 1e6 / g.cfg.totalUnits;
    for (int s = 0; s < NSLICES; ++s)
    {
        DataRate r(uint64_t(units[s] * perUnitBps));
        g_pipeTx[s]->SetDataRate(r);
        g_pipeRx[s]->SetDataRate(r);
    }
    g.alloc = units;
}

static std::vector<std::array<int, NSLICES>> RlActions()
{
    std::vector<std::array<int, NSLICES>> actions;
    for (int e = 10; e <= 80; e += 10)
        for (int u = 10; u <= 80; u += 10)
        {
            int m = 100 - e - u;
            if (m >= 10 && m <= 80)
                actions.push_back({e, u, m});
        }
    return actions;
}

static std::vector<std::array<int, NSLICES>> g_rlActions = RlActions();
static Ptr<class SliceRlEnv> g_rlEnv;
static uint32_t g_rlStep = 0;
static bool g_rlMode = false;
enum PolicyMode { POLICY_STATIC = 0, POLICY_RANDOM = 1, POLICY_ADAPTIVE = 2 };
static PolicyMode g_policyMode = POLICY_STATIC;
static void WriteTimeSeries(const std::string& path);

static std::array<int, NSLICES> HeuristicAction()
{
    std::array<int, NSLICES> a = {50, 30, 20};
    double e = g.demand[EMBB];
    double u = g.demand[URLLC];
    double m = g.demand[MMTC];

    if (m > 2.0)
        a = {35, 20, 45};
    else if (u > 7.0)
        a = {35, 45, 20};
    else if (e > 12.0)
        a = {55, 25, 20};
    else if (u > 4.0)
        a = {40, 38, 22};
    else if (m > 1.0)
        a = {40, 25, 35};

    int sum = a[0] + a[1] + a[2];
    if (sum != 100)
    {
        int delta = 100 - sum;
        a[2] += delta;
    }
    return a;
}

static std::array<int, NSLICES> PolicyAction()
{
    if (g_policyMode == POLICY_STATIC)
        return g.cfg.staticAlloc;
    if (g_policyMode == POLICY_RANDOM)
        return g_rlActions[std::rand() % g_rlActions.size()];
    return HeuristicAction();
}

static void PolicyStep()
{
    if (g_rlMode || g_policyMode == POLICY_STATIC || Simulator::Now().GetSeconds() >= g.cfg.duration)
        return;
    ApplyAllocation(PolicyAction());
    STDOUT("[" << Simulator::Now().GetSeconds() << "s] policy='" << (g_policyMode == POLICY_RANDOM ? "random" : "adaptive")
                      << "' allocation=" << g.alloc[0] << "/" << g.alloc[1] << "/" << g.alloc[2]);
    Simulator::Schedule(Seconds(1.0), &PolicyStep);
}

class SliceRlEnv : public OpenGymEnv
{
  public:
    SliceRlEnv()
    {
        SetOpenGymInterface(OpenGymInterface::Get());
    }

    Ptr<OpenGymSpace> GetActionSpace() override
    {
        return CreateObject<OpenGymDiscreteSpace>(g_rlActions.size());
    }

    Ptr<OpenGymSpace> GetObservationSpace() override
    {
        std::vector<uint32_t> shape = {10};
        return CreateObject<OpenGymBoxSpace>(0.0, 1.0, shape, TypeNameGet<float>());
    }

    bool GetGameOver() override
    {
        return g_rlStep >= 50;
    }

    Ptr<OpenGymDataContainer> GetObservation() override
    {
        std::vector<uint32_t> shape = {10};
        auto box = CreateObject<OpenGymBoxContainer<float>>(shape);
        const double total = g.cfg.totalCapacityMbps;
        const double eCap = std::max(0.001, g.alloc[EMBB] * total / g.cfg.totalUnits);
        const double uCap = std::max(0.001, g.alloc[URLLC] * total / g.cfg.totalUnits);
        const double mCap = std::max(0.001, g.alloc[MMTC] * total / g.cfg.totalUnits);
        box->AddValue(float(std::clamp(g.demand[EMBB] / total, 0.0, 1.0)));
        box->AddValue(float(std::clamp(g.demand[URLLC] / total, 0.0, 1.0)));
        box->AddValue(float(std::clamp(g.demand[MMTC] / total, 0.0, 1.0)));
        box->AddValue(float(g.alloc[EMBB] / 100.0));
        box->AddValue(float(g.alloc[URLLC] / 100.0));
        box->AddValue(float(g.alloc[MMTC] / 100.0));
        box->AddValue(float(std::clamp(std::min(g.demand[EMBB] / eCap, 1.0), 0.0, 1.0)));
        box->AddValue(float(std::clamp((g.demand[URLLC] / uCap) * 0.5, 0.0, 1.0)));
        box->AddValue(float(std::clamp(std::max(0.0, g.demand[URLLC] - uCap) / total, 0.0, 1.0)));
        box->AddValue(float(std::clamp(std::min(g.demand[MMTC] / mCap, 1.0), 0.0, 1.0)));
        return box;
    }

    float GetReward() override
    {
        const double total = g.cfg.totalCapacityMbps;
        double reward = 0.0;
        for (int s = 0; s < NSLICES; ++s)
        {
            double cap = g.alloc[s] * total / g.cfg.totalUnits;
            double carried = std::min(g.demand[s], cap);
            double loss = g.demand[s] > 0 ? (g.demand[s] - carried) / g.demand[s] : 0.0;
            reward += carried / total;
            reward -= (s == URLLC ? 4.0 : 1.0) * loss;
        }
        double uCap = g.alloc[URLLC] * total / g.cfg.totalUnits;
        double uUtil = g.demand[URLLC] / std::max(0.001, uCap);
        reward -= 2.0 * std::max(0.0, uUtil - 0.85);
        return float(reward);
    }

    std::string GetExtraInfo() override
    {
        std::ostringstream out;
        out << "step=" << g_rlStep << ",allocation=" << g.alloc[0] << "/" << g.alloc[1] << "/"
            << g.alloc[2];
        return out.str();
    }

    bool ExecuteActions(Ptr<OpenGymDataContainer> action) override
    {
        auto discrete = DynamicCast<OpenGymDiscreteContainer>(action);
        if (!discrete || discrete->GetValue() >= g_rlActions.size())
            return false;
        ApplyAllocation(g_rlActions[discrete->GetValue()]);
        return true;
    }
};

static void RlStep()
{
    if (!g_rlMode || !g_rlEnv)
        return;
    if (g_rlStep >= 50)
    {
        WriteTimeSeries(g.cfg.outPrefix + "_timeseries.csv");
        STDOUT("Wrote " << g.cfg.outPrefix << "_timeseries.csv");
        g_rlEnv->NotifySimulationEnd();
        return;
    }
    ++g_rlStep;
    g_rlEnv->Notify();
    Simulator::Schedule(Seconds(1.0), &RlStep);
}

// ===========================================================================
// 5. TRAFFIC PHASES
// ===========================================================================
static std::vector<Ptr<SliceSource>> g_embbApps, g_urllcApps, g_mmtcApps;

static void ApplyPhase(Phase ph)
{
    for (auto& a : g_embbApps)  a->SetRate(ph.embbMbps / g_embbApps.size());
    for (auto& a : g_urllcApps) a->SetRate(ph.urllcMbps / g_urllcApps.size());
    for (uint32_t i = 0; i < g_mmtcApps.size(); ++i)
        g_mmtcApps[i]->SetActive(i < ph.mmtcDevices);

    double mmtcMbps = ph.mmtcDevices * g.cfg.mmtcPktPerSec * g.cfg.pktMmtc * 8 / 1e6;
    g.demand = {ph.embbMbps, ph.urllcMbps, mmtcMbps};
    STDOUT("[" << Simulator::Now().GetSeconds() << "s] phase '" << ph.label
                      << "': eMBB " << ph.embbMbps << " Mbps, URLLC " << ph.urllcMbps
                      << " Mbps, mMTC " << ph.mmtcDevices << " devices");
}

// ===========================================================================
// 6. TOPOLOGY HELPERS
// ===========================================================================
static Ipv4AddressHelper g_addr;
static uint32_t g_subnet = 0;

static Ipv4InterfaceContainer NextSubnet(NetDeviceContainer d)
{
    std::ostringstream net;
    net << "10." << (1 + g_subnet / 256) << "." << (g_subnet % 256) << ".0";
    g_subnet++;
    g_addr.SetBase(net.str().c_str(), "255.255.255.0");
    return g_addr.Assign(d);
}

// Connect n devices to a gateway; returns device nodes and their IPs
static NodeContainer AttachDevices(Ptr<Node> gw, uint32_t n, int slice,
                                   PointToPointHelper& access)
{
    NodeContainer devs;
    devs.Create(n);
    InternetStackHelper().Install(devs);
    for (uint32_t i = 0; i < n; ++i)
    {
        NetDeviceContainer d = access.Install(devs.Get(i), gw);
        Ipv4InterfaceContainer ifc = NextSubnet(d);
        g.addrToDev[ifc.GetAddress(0).Get()] = {slice, i};
    }
    return devs;
}

// ===========================================================================
// 7. OUTPUT
// ===========================================================================
static double Percentile(std::vector<double> v, double q)
{
    if (v.empty()) return NAN;
    std::sort(v.begin(), v.end());
    size_t k = std::min(v.size() - 1, size_t(q * (v.size() - 1) + 0.5));
    return v[k];
}

static void WriteTimeSeries(const std::string& path)
{
    std::ofstream f(path);
    f << "run,time,slice,alloc_units,capacity_mbps,demand_mbps,tx_pkts,delivered_of_tx,"
         "rx_pkts,throughput_mbps,wire_mbps,delay_mean_ms,delay_p95_ms,urllc_viol,"
         "mmtc_active,mmtc_served\n";
    double perUnit = g.cfg.totalCapacityMbps / g.cfg.totalUnits;
    int nb = int(g.cfg.duration / g.cfg.binS);
    for (int b = 0; b < nb; ++b)
    {
        for (int s = 0; s < NSLICES; ++s)
        {
            const Bin& x = g.bins[s][b];
            double thr = x.rxBytes * 8.0 / g.cfg.binS / 1e6;
            double wire = (x.rxBytes + x.rx * WIRE_OVERHEAD) * 8.0 / g.cfg.binS / 1e6;
            double mean = x.delayMs.empty() ? NAN
                          : std::accumulate(x.delayMs.begin(), x.delayMs.end(), 0.0) / x.delayMs.size();
            uint64_t viol = 0;
            if (s == URLLC)
                for (double d : x.delayMs) viol += (d > g.cfg.urllcTargetMs);
            int active = 0, served = 0;
            if (s == MMTC)
                for (uint32_t i = 0; i < g.cfg.nMmtc; ++i)
                    if (g.mmtcTx[i][b] > 0)
                    {
                        active++;
                        if (double(g.mmtcOk[i][b]) / g.mmtcTx[i][b] >= g.cfg.mmtcServedPdr) served++;
                    }
            f << g.cfg.run << "," << b * g.cfg.binS << "," << SLICE_NAME[s] << ","
              << g.allocLog[b][s] << "," << g.allocLog[b][s] * perUnit << ","
              << g.demandLog[b][s] << "," << x.tx << "," << x.rxOfTx << "," << x.rx << ","
              << thr << "," << wire << "," << mean << "," << Percentile(x.delayMs, 0.95) << ","
              << viol << "," << active << "," << served << "\n";
        }
    }
}

// ===========================================================================
// 8. MAIN
// ===========================================================================
int main(int argc, char* argv[])
{
    SimConfig& c = g.cfg;
    std::string alloc = "50,30,20";
    std::string policy = "static";
    CommandLine cmd(__FILE__);
    cmd.AddValue("run", "RNG run number (seed)", c.run);
    cmd.AddValue("alloc", "static allocation eMBB,URLLC,mMTC (units, sum=100)", alloc);
    cmd.AddValue("queue", "slice pipe queue size (packets)", c.pipeQueuePkts);
    cmd.AddValue("target", "URLLC latency target (ms)", c.urllcTargetMs);
    cmd.AddValue("out", "output file prefix", c.outPrefix);
    cmd.AddValue("policy", "native non-DQN policy: static, random, adaptive", policy);
    cmd.AddValue("rl", "enable ns3-ai Gym control (Python chooses allocation every 1 s)", g_rlMode);
    cmd.Parse(argc, argv);
    {
        std::stringstream ss(alloc); std::string tok; int i = 0;
        while (std::getline(ss, tok, ',') && i < NSLICES) c.staticAlloc[i++] = std::stoi(tok);
    }
    if (policy == "random")
        g_policyMode = POLICY_RANDOM;
    else if (policy == "adaptive")
        g_policyMode = POLICY_ADAPTIVE;
    else
        g_policyMode = POLICY_STATIC;
    RngSeedManager::SetSeed(12345);
    RngSeedManager::SetRun(c.run);

    // ---- measurement storage ----
    g.nBins = int((c.duration + c.drain) / c.binS) + 1;
    for (int s = 0; s < NSLICES; ++s) g.bins[s].resize(g.nBins);
    g.mmtcTx.assign(c.nMmtc, std::vector<uint32_t>(g.nBins, 0));
    g.mmtcOk.assign(c.nMmtc, std::vector<uint32_t>(g.nBins, 0));
    g.allocLog.resize(g.nBins);
    g.demandLog.resize(g.nBins);

    // ---- core nodes ----
    Ptr<Node> bs = CreateObject<Node>();
    NodeContainer gws; gws.Create(NSLICES);
    InternetStackHelper stack;
    stack.Install(bs);
    stack.Install(gws);

    // ---- slice pipes (GW -> BS), explicit FIFO queue ----
    PointToPointHelper pipe;
    pipe.SetChannelAttribute("Delay", StringValue(c.pipeDelay));
    pipe.SetDeviceAttribute("DataRate", StringValue("1Mbps")); // overwritten by ApplyAllocation
    pipe.SetQueue("ns3::DropTailQueue", "MaxSize", StringValue("1p"));

    TrafficControlHelper fifo;
    fifo.SetRootQueueDisc("ns3::FifoQueueDisc", "MaxSize",
                          QueueSizeValue(QueueSize(std::to_string(c.pipeQueuePkts) + "p")));

    for (int s = 0; s < NSLICES; ++s)
    {
        NetDeviceContainer d = pipe.Install(gws.Get(s), bs);
        fifo.Install(d);           // install BEFORE address assignment -> no default fq_codel
        NextSubnet(d);
        g_pipeTx[s] = DynamicCast<PointToPointNetDevice>(d.Get(0));
        g_pipeRx[s] = DynamicCast<PointToPointNetDevice>(d.Get(1));
    }

    // ---- access links (UE -> GW), never the bottleneck ----
    PointToPointHelper access;
    access.SetDeviceAttribute("DataRate", StringValue(c.accessRate));
    access.SetChannelAttribute("Delay", StringValue(c.accessDelay));

    NodeContainer embbUe  = AttachDevices(gws.Get(EMBB),  c.nEmbb,  EMBB,  access);
    NodeContainer urllcUe = AttachDevices(gws.Get(URLLC), c.nUrllc, URLLC, access);
    NodeContainer mmtcUe  = AttachDevices(gws.Get(MMTC),  c.nMmtc,  MMTC,  access);
    Ipv4GlobalRoutingHelper::PopulateRoutingTables();

    // ---- sinks on BS, one UDP port per slice ----
    Ipv4Address bsAddr = bs->GetObject<Ipv4>()->GetAddress(1, 0).GetLocal();
    std::array<uint16_t, NSLICES> port = {9001, 9002, 9003};
    for (int s = 0; s < NSLICES; ++s)
    {
        Ptr<Socket> sink = Socket::CreateSocket(bs, UdpSocketFactory::GetTypeId());
        sink->Bind(InetSocketAddress(Ipv4Address::GetAny(), port[s]));
        sink->SetRecvCallback(MakeCallback(&OnRx));
    }

    // ---- sources ----
    std::vector<Phase> scenario = MakeScenario();
    const Phase& p0 = scenario.front();
    int64_t stream = 100;
    auto makeApps = [&](NodeContainer& nodes, int s, uint32_t pkt, double rate, bool poisson,
                        std::vector<Ptr<SliceSource>>& out) {
        for (uint32_t i = 0; i < nodes.GetN(); ++i)
        {
            Ptr<SliceSource> a = CreateObject<SliceSource>();
            a->Setup(InetSocketAddress(bsAddr, port[s]), pkt, rate, poisson, s, i, stream);
            stream += 2;
            nodes.Get(i)->AddApplication(a);
            a->SetStartTime(Seconds(0.0));
            a->SetStopTime(Seconds(c.duration));
            out.push_back(a);
        }
    };
    double mmtcDevMbps = c.mmtcPktPerSec * c.pktMmtc * 8 / 1e6;
    makeApps(embbUe,  EMBB,  c.pktEmbb,  p0.embbMbps / c.nEmbb,   false, g_embbApps);  // CBR video-like
    makeApps(urllcUe, URLLC, c.pktUrllc, p0.urllcMbps / c.nUrllc, true,  g_urllcApps); // Poisson
    makeApps(mmtcUe,  MMTC,  c.pktMmtc,  mmtcDevMbps,             true,  g_mmtcApps);  // Poisson

    // ---- static allocation + phases ----
    ApplyAllocation(c.staticAlloc);
    for (const Phase& ph : scenario)
        Simulator::Schedule(Seconds(ph.start), &ApplyPhase, ph);
    Simulator::Schedule(Seconds(c.binS / 2), &LogBin, 0);

    if (g_rlMode)
    {
        g_rlEnv = CreateObject<SliceRlEnv>();
        g_rlStep = 0;
        Simulator::Schedule(Seconds(1.0), &RlStep);
        Simulator::Schedule(Seconds(c.duration),
                            &WriteTimeSeries,
                            c.outPrefix + "_timeseries.csv");
    }
    else if (g_policyMode != POLICY_STATIC)
    {
        Simulator::Schedule(Seconds(1.0), &PolicyStep);
    }

    STDOUT("Policy mode=" << (g_rlMode ? "dqn" : (g_policyMode == POLICY_RANDOM ? "random" : (g_policyMode == POLICY_ADAPTIVE ? "adaptive" : "static")))
                  << ", allocation eMBB/URLLC/mMTC = " << c.staticAlloc[0] << "/"
                  << c.staticAlloc[1] << "/" << c.staticAlloc[2] << " units, run " << c.run);

    Simulator::Stop(Seconds(c.duration + c.drain));
    Simulator::Run();

    WriteTimeSeries(c.outPrefix + "_timeseries.csv");
    STDOUT("Wrote " << c.outPrefix << "_timeseries.csv");
    Simulator::Destroy();
    return 0;
}
