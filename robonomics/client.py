# create rsa pair
# send demand
# wait for result
# read the result
# decrypt message
import rsa
import rospy
from rosbag import Bag
from robonomics_msgs.msg import Demand, Result
from std_msgs.msg import String

from ethereum_common.srv import Accounts, BlockNumber
from ipfs_common.msg import Multihash
from ipfs_common.ipfs_rosbag import IpfsRosBag
from ethereum_common.msg import Address, UInt256

MODEL = "QmaTLSFvFh2gTv5eUDfpE1YZjiwuPwSq9RpSG9kSJ6Y9W1"
TOKEN = "0x7dE91B204C1C737bcEe6F000AAA6569Cf7061cb7"
LIGHTHOUSE = "0xD40AC7F1e5401e03D00F5aeC1779D8e5Af4CF9f1"
LIFETIME = 100

class ClientRSA:
    def __init__(self):
        rospy.init_node("client_rsa_node")
        rospy.loginfo("Launching ClientRSA node...")

        rospy.wait_for_service('/eth/current_block')
        rospy.wait_for_service('/eth/accounts')
        self.accounts = rospy.ServiceProxy('/eth/accounts', Accounts)()
        rospy.loginfo(str(self.accounts))  # AIRA ethereum addresses

        rospy.loginfo("Generating new pair of keys...")
        (pubkey, privkey) = rsa.newkeys(512)

        self.pubkey = pubkey
        self.privkey = privkey

        rospy.loginfo("Public key: {}".format(pubkey))
        rospy.loginfo("Private key: {}".format(privkey))

        self.signing_demand = rospy.Publisher('/liability/infochan/eth/signing/demand', Demand, queue_size=128)
        self.incoming_result = rospy.Subscriber("/liability/infochan/incoming/result", Result, self.on_result)

        self.make_demand()

        rospy.loginfo("ClientRSA node is launched")

    def create_objective(self) -> Multihash:
        topics = {
                "/pubkey": [String(self.pubkey.save_pkcs1().decode("utf-8"))],
                "/task": [String("Do the work!")]
                }
        rospy.loginfo(topics)
        obj = IpfsRosBag(messages=topics)
        return obj.multihash

    def make_deadline(self) -> str:
        lifetime = LIFETIME
        deadline = rospy.ServiceProxy('/eth/current_block', BlockNumber)().number + lifetime
        return str(deadline)


    def make_demand(self):
        rospy.loginfo("Making demand...")

        demand = Demand()
        demand.model = Multihash(multihash=MODEL)
        demand.objective = self.create_objective()
        demand.token = Address(address=TOKEN)
        demand.cost = UInt256("0")
        demand.lighthouse = Address(address=LIGHTHOUSE)
        demand.validatorFee = UInt256("0")
        demand.validator = Address("0x0000000000000000000000000000000000000000")
        demand.deadline = UInt256()
        demand.deadline.uint256 = self.make_deadline()
        rospy.loginfo(demand)

        self.signing_demand.publish(demand)

    def on_result(self, res: Result):
        rospy.loginfo("Got a result: {}".format(res))

        res = IpfsRosBag(multihash=res.result)
        rospy.loginfo(res.messages)

        for k, v in res.messages.items():
            if k.endswith("data"):
                hex_string = v[0].data
                to_decrypt = bytearray.fromhex(hex_string)
                decrypted = rsa.decrypt(to_decrypt, self.privkey).decode("utf-8")
                rospy.loginfo(decrypted)

    def spin(self):
        rospy.spin()

if __name__ == "__main__":
    ClientRSA().spin()

